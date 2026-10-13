"""Optional card delivery, independent from the accepted main alert."""
import asyncio
from datetime import UTC,datetime,timedelta
from hashlib import sha256
from google.genai.errors import APIError
from pydantic import ValidationError
from api.offline_card import CardContext,CardChoice,card_text,card_from_storage
from api.card_renderer import render_offline_card
from api.destinations import SafePoint
from api.dispatch_models import LiftItem
from api.demo_scenario import current_scenario,scenario_collection,event_is_current
from api.agents.sessions import session_user_id
from api.i18n import text
from api.inventory_models import InventoryReply
from api.tools.telegram import TelegramSendError

class OfflineCardService:
    def __init__(self,store,telegram,risk,reader,destinations,selector,assets_factory,*,hash_salt):
        self.store,self.telegram,self.risk,self.reader,self.destinations,self.selector=store,telegram,risk,reader,destinations,selector
        self.assets_factory,self.hash_salt=assets_factory,hash_salt
        self.assets=None;self.tasks=set();self._slots=asyncio.Semaphore(1)

    def _point(self,shop,kind):
        destination=self.destinations.nearest(shop['lat'],shop['lng'],(kind,))
        if destination is None or not destination.safe_point_id:return None
        snapshot=self.store.client.collection(self.destinations.collection).document(destination.safe_point_id).get(timeout=8,retry=None)
        value=snapshot.to_dict()
        if not value:return None
        point=SafePoint.model_validate(dict(value,safe_point_id=snapshot.id))
        if point.is_demo or point.type!=kind or point.opening_status=='closed':return None
        if (point.lat,point.lng,point.name)!=(destination.lat,destination.lng,destination.name):raise ValueError('Destination changed while freezing card')
        return point

    def _guard(self,context,event):
        state=self.risk.get(context.shop_id)
        if state.active_danger or (context.episode_id and state.episode_id!=context.episode_id):return False
        scenario=self.store.scenario() if context.is_demo else {}
        return event_is_current(event,scenario,context.shop_id)

    async def _freeze(self,identity,shop,language,event):
        previous=await asyncio.to_thread(self.store.get,identity)
        if previous:return card_from_storage(previous['context'])
        items=tuple(LiftItem.model_validate(row) for row in shop.get('lift_first',[])[:5]) if shop.get('baseline_inventory_id') else ()
        parking=await asyncio.to_thread(self._point,shop,'parking')
        shelter=await asyncio.to_thread(self._point,shop,'pps')
        return CardContext(card_id=identity,shop_id=shop['shop_id'],shop_name=shop['shop_name'],language=language,lat=shop['lat'],lng=shop['lng'],inventory_id=shop.get('baseline_inventory_id'),items=items,displayed_value_rm=sum(item.value_rm for item in items),parking=parking,shelter=shelter,prepared_at=event['created_at'],is_demo=bool(shop.get('is_demo')),episode_id=event.get('episode_id'),event_id=event['event_id'],scenario_generation=event.get('scenario_generation'))

    async def _choose(self,context):
        fallback=CardChoice()
        if self.selector is None:return fallback
        # Single total budget, at most one invalid/transient retry; permanent errors fall back.
        try:
            async with asyncio.timeout(20):
                for attempt in range(2):
                    try:return await self.selector(context)
                    except APIError as error:
                        if error.code not in (429,500,502,503,504) or attempt:break
                    except (TimeoutError,ValidationError,ValueError):
                        if attempt:break
        except Exception:pass
        return fallback

    async def deliver(self,identity):
        async with self._slots:return await self._deliver_once(identity)

    async def _deliver_once(self,identity):
        status,owner=await asyncio.to_thread(self.store.claim,identity)
        if status!='claimed':return status
        risk_owner=None;context=None;external_started=False
        try:
            record=await asyncio.to_thread(self.store.get,identity)
            context=card_from_storage(record['context']);event=record['event']
            if not await asyncio.to_thread(self._guard,context,event):
                await asyncio.to_thread(self.store.update,identity,owner,status='superseded');return 'superseded'
            choice=CardChoice.model_validate(record['choice']) if record.get('choice') else await self._choose(context)
            await asyncio.to_thread(self.store.update,identity,owner,choice=choice.model_dump())
            words=card_text(context,choice)
            if self.assets is None:self.assets=await asyncio.to_thread(self.assets_factory)
            if record.get('asset_path'):
                data=await asyncio.to_thread(self.assets.read,record['asset_path'],record['asset_sha256'])
            else:
                data=await asyncio.to_thread(render_offline_card,context,words)
                path,digest=await asyncio.to_thread(self.assets.write,identity,data)
                await asyncio.to_thread(self.store.update,identity,owner,asset_path=path,asset_sha256=digest)
                data=await asyncio.to_thread(self.assets.read,path,digest)
            disposition,risk_owner=await asyncio.to_thread(self.risk.claim_delivery,context.shop_id,event)
            if disposition!='claimed':
                await asyncio.to_thread(self.store.update,identity,owner,status='retryable' if disposition=='busy' else 'superseded',lease_until=datetime.now(UTC))
                return disposition
            await asyncio.to_thread(self.store.update,identity,owner,status='sending',lease_until=datetime.now(UTC)+timedelta(seconds=30))
            # Canonical Danger/generation is checked after model/render/store awaits, right before send.
            if not await asyncio.to_thread(self._guard,context,event):
                await asyncio.to_thread(self.store.update,identity,owner,status='superseded');return 'superseded'
            caption=words.footer
            if context.is_demo:caption=text(context.language,'card_simulation')+'\n'+caption
            external_started=True
            message_id=await asyncio.to_thread(self.telegram.send_photo,record['chat_id'],data,caption)
            await asyncio.to_thread(self.store.update,identity,owner,status='accepted',message_id=message_id,accepted_at=datetime.now(UTC))
            return 'accepted'
        except asyncio.CancelledError:
            if external_started:
                await asyncio.shield(asyncio.to_thread(self.store.update,identity,owner,status='uncertain'))
                risk_owner=None # The underlying thread may still send; retain its bounded risk lease.
            raise
        except TelegramSendError as error:
            await asyncio.to_thread(self.store.update,identity,owner,status='uncertain' if error.uncertain else 'retryable',lease_until=datetime.now(UTC))
            return 'uncertain' if error.uncertain else 'retryable'
        except Exception:
            # After an external call began, a persistence failure cannot authorize another image.
            await asyncio.to_thread(self.store.update,identity,owner,status='uncertain' if external_started else 'retryable',lease_until=datetime.now(UTC))
            return 'uncertain' if external_started else 'retryable'
        finally:
            if risk_owner is not None and context is not None:await asyncio.to_thread(self.risk.release_delivery,context.shop_id,risk_owner)

    def _schedule(self,identity):
        task=asyncio.create_task(self.deliver(identity));self.tasks.add(task)
        def finished(task):
            self.tasks.discard(task)
            if not task.cancelled():task.exception() # durable retry remains; never log SDK/token payloads.
        task.add_done_callback(finished)

    async def enqueue_watch(self,event,shop,recipient,alert_id):
        if event['level']!='watch':return None
        if hasattr(recipient,'key'):return 'virtual_skipped' # no fake chat IDs or image acceptance counts.
        identity=sha256(('watch-card:'+alert_id).encode()).hexdigest()
        raw=shop.model_dump();raw['shop_id']=shop.shop_id
        context=await self._freeze(identity,raw,recipient.language,event)
        await asyncio.to_thread(self.store.begin,context,recipient.telegram_chat_id,event)
        self._schedule(identity);return identity

    async def request_owner(self,chat_id,operation_id):
        shop=await asyncio.to_thread(self.reader.shop_for_sender,chat_id)
        member=next((m for m in (shop or {}).get('recipients',[]) if m.get('telegram_chat_id')==chat_id and m.get('role')=='owner'),None)
        if not shop or not member:return 'unavailable',InventoryReply(text=text('en','card_owner_required'),kind='unavailable')
        language=member['language'];state=await asyncio.to_thread(self.risk.get,shop['shop_id'])
        if state.active_danger:return 'danger',await self.danger_reply(shop,language)
        identity=sha256(f"owner-card:{shop['shop_id']}:{session_user_id(chat_id,self.hash_salt)}:{operation_id}".encode()).hexdigest()
        now=datetime.now(UTC)
        scenario=await asyncio.to_thread(self.store.scenario) if shop.get('is_demo') else {}
        event={'event_id':identity,'source':'card_request','level':'watch','created_at':now,'is_demo':bool(shop.get('is_demo')),'episode_id':state.episode_id,'scenario_generation':scenario.get('generation',0)}
        context=await self._freeze(identity,shop,language,event)
        record=await asyncio.to_thread(self.store.begin,context,chat_id,event)
        status=await self.deliver(record['card_id'])
        if status=='accepted':return status,None
        if (await asyncio.to_thread(self.risk.get,shop['shop_id'])).active_danger:return 'danger',await self.danger_reply(shop,language)
        return status,InventoryReply(text=text(language,'card_unavailable'),shop_id=shop['shop_id'],language=language,is_demo=bool(shop.get('is_demo')),kind='unavailable')

    async def danger_reply(self,shop,language):
        from api.alert_composer import render_danger
        destination=await asyncio.to_thread(self.destinations.nearest,shop['lat'],shop['lng'],('pps','high_ground'))
        message,markup=render_danger(language,bool(shop.get('is_demo')),destination)
        return InventoryReply(text=message,reply_markup=markup,shop_id=shop['shop_id'],language=language,is_demo=bool(shop.get('is_demo')),kind='danger')

    async def resume_pending(self,limit=20):
        return [await self.deliver(identity) for identity in await asyncio.to_thread(self.store.pending_ids,limit)]

    async def close(self):
        for task in tuple(self.tasks):task.cancel()
        if self.tasks:await asyncio.gather(*tuple(self.tasks),return_exceptions=True)
        if self.selector is not None:await self.selector.close()
        if self.assets is not None:await asyncio.to_thread(self.assets.client.close)
        self.store.client.close()

class LazyOfflineCardService:
    """No model/storage clients are constructed for unrelated text or Danger."""
    def __init__(self,settings):self.settings,self.active=settings,None
    def _service(self):
        if self.active is None:
            from api.tools.firestore import create_firestore_client
            from api.tools.storage import create_storage_client
            from api.tools.telegram import TelegramAPI
            from api.active_risk import ActiveRiskStore
            from api.photo_store import PhotoStore
            from api.destinations import DestinationLookup
            from api.offline_card_store import FirestoreCardStore
            from api.card_assets import CardAssets
            from api.agents.offline_card import CardSelector
            client=create_firestore_client(self.settings)
            def assets():
                if not self.settings.gcs_bucket:raise ValueError('GCS_BUCKET is required for card assets')
                return CardAssets(create_storage_client(self.settings),self.settings.gcs_bucket)
            self.active=OfflineCardService(FirestoreCardStore(client),TelegramAPI(self.settings.telegram_bot_token),ActiveRiskStore(client,max_age=self.settings.official_max_age),PhotoStore(client,self.settings.hash_salt),DestinationLookup(client,radius_m=self.settings.destination_search_radius_m),CardSelector(self.settings),assets,hash_salt=self.settings.hash_salt)
        return self.active
    async def enqueue_watch(self,*args):return await (await asyncio.to_thread(self._service)).enqueue_watch(*args)
    async def request_owner(self,*args):return await (await asyncio.to_thread(self._service)).request_owner(*args)
    async def deliver(self,identity):return await (await asyncio.to_thread(self._service)).deliver(identity)
    async def close(self):
        if self.active is not None:await self.active.close()
