"""Public lookup orchestration with transient points and durable sanitized replay."""
import asyncio
from datetime import UTC,datetime
import time
from typing import Awaitable,Callable,TypeVar
from api.public_check_store import FirestoreCheckIntentStore,IntentDecision
from api.public_check import PublicCheckReader
from api.agents.public_check import CheckSummarizer
T=TypeVar("T")
from pydantic import Field
from api.reply_guard import ReplyGuard,Shop
from api.photo_store import PhotoStore
from api.destinations import DestinationLookup
from api.config import Settings
from api.inventory_models import InventoryReply
from api.i18n import text,catalog,LANGUAGES
from api.public_check_models import CheckLocation,CheckResult
from api.public_check import fixed_check_danger
from api.agents.public_check import expected_choice

class CheckReply(InventoryReply):
    intent_id:str|None=Field(default=None,pattern=r'^[0-9a-f]{64}$')
    location_request:bool=False

class PublicCheckService:
    def __init__(self,store:PhotoStore,intents:FirestoreCheckIntentStore,reader:PublicCheckReader,summarizer:CheckSummarizer,*,destinations:DestinationLookup|None=None,clock:Callable[[],datetime]|None=None,total_budget_seconds:float=25,owns_clients:bool=False)->None:
        if not 0<total_budget_seconds<=25:raise ValueError('Public lookup budget must be bounded')
        self.store=store;self.guard=ReplyGuard(store,destinations=destinations)
        self.intents,self.reader,self.summarizer=intents,reader,summarizer
        self.clock=clock or (lambda:datetime.now(UTC));self.budget=total_budget_seconds;self.owns_clients=owns_clients;self.pending=set()

    async def danger_reply(self,shop:Shop)->InventoryReply:
        return await self.guard.danger_reply(shop)

    async def reply(self,shop:Shop|None,key:str)->InventoryReply:
        return await self.guard.reply(shop,key)

    async def _bounded(self,awaitable:Awaitable[T],deadline:float)->T:
        task=asyncio.ensure_future(awaitable);self.pending.add(task)
        def finished(item):
            self.pending.discard(item)
            if not item.cancelled():item.exception() # Observe background failures without payload logging.
        task.add_done_callback(finished)
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Lookup budget elapsed')
        async with asyncio.timeout(remaining):return await asyncio.shield(task)

    async def _shop(self,sender:int)->Shop|None:return await asyncio.to_thread(self.store.shop_for_sender,sender)
    async def _reply(self,sender:int,key:str,*,language:str|None=None,intent_id:str|None=None,location_request:bool=False)->InventoryReply:
        shop=await self._shop(sender)
        if shop and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        language=language if language in LANGUAGES else shop.get('language','en') if shop else 'en'
        rendered=text(language,key)
        if not catalog(language)['_reviewed']:rendered+='\n'+text(language,'translation_notice')
        markup={'keyboard':[[{'text':text(language,'check_location_button'),'request_location':True}]],'resize_keyboard':True,'one_time_keyboard':True} if location_request else {'remove_keyboard':True}
        return CheckReply(text=rendered,kind='prompt' if location_request else 'unavailable',reply_markup=markup,language=language,intent_id=intent_id,location_request=location_request)

    async def start(self,sender:int,operation:str,*,registered_flow_waiting:bool=False,language_hint:str|None=None)->InventoryReply:
        shop=await self._shop(sender)
        if shop and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        language=shop.get('language','en') if shop else language_hint if language_hint in LANGUAGES else 'en'
        if registered_flow_waiting:return await self._reply(sender,'check_existing_location',language=language)
        decision=await asyncio.to_thread(self.intents.open,sender,operation,self.clock(),language=language)
        if decision.status!='waiting_location':return await self._reply(sender,'check_expired',language=language)
        return await self._reply(sender,'check_request_location',language=decision.language,intent_id=decision.intent_id,location_request=True)

    async def context(self,sender:int,operation:str)->tuple[IntentDecision|None,bool]:
        bound=await asyncio.to_thread(self.intents.bound,sender,operation,self.clock())
        if bound.status!='none':return bound,True
        active=await asyncio.to_thread(self.intents.active,sender,self.clock())
        return (active,False) if active.status=='waiting_location' else (None,False)

    async def lookup(self,sender:int,operation:str,location:CheckLocation,context:IntentDecision)->InventoryReply:
        deadline=time.monotonic()+self.budget;claim=None;language=context.language
        try:
            shop=await self._bounded(self._shop(sender),deadline)
            if shop and await self._bounded(asyncio.to_thread(self.store.danger_active,shop['shop_id']),deadline):return await self.danger_reply(shop)
            claim=await self._bounded(asyncio.to_thread(self.intents.claim,sender,context.intent_id,operation,self.clock()),deadline)
            if claim.status=='complete':return self.render(claim.result,language,claim.intent_id)
            if claim.status!='claimed':return await self._reply(sender,'check_rate_limited' if claim.status in ('rate_limited','busy') else 'check_expired',language=language)
            result=await self._bounded(self.reader.read(location),min(deadline,time.monotonic()+14))
            current_shop=await self._bounded(self._shop(sender),deadline)
            if current_shop and await self._bounded(asyncio.to_thread(self.store.danger_active,current_shop['shop_id']),deadline):
                try:await self._bounded(asyncio.to_thread(self.intents.retryable,sender,claim.intent_id,claim.owner,self.clock()),deadline)
                except Exception:pass
                return await self.danger_reply(current_shop)
            selected_key=None
            # Danger never reaches optional generation.
            if result.level!='danger':
                try:
                    choice=await self._bounded(self.summarizer.summarize(result,budget_seconds=min(8,max(.001,deadline-time.monotonic()-5))),deadline)
                    selected_key=choice.key if choice.key==expected_choice(result) else expected_choice(result)
                except Exception:pass # Canonical factual rendering is the same bounded fallback.
            completed=await self._bounded(asyncio.to_thread(self.intents.finish,sender,claim.intent_id,claim.owner,result,self.clock()),deadline)
            if completed.status!='complete':return await self._reply(sender,'check_expired',language=language)
            return self.render(completed.result,language,completed.intent_id,selected_key)
        except Exception:
            if claim and claim.status=='claimed':
                try:await self._bounded(asyncio.to_thread(self.intents.retryable,sender,claim.intent_id,claim.owner,self.clock()),deadline)
                except Exception:pass # Underlying bounded work is retained; the60s claim lease remains the fallback fence.
            notice='\n'+text(language,'translation_notice') if not catalog(language)['_reviewed'] else ''
            return CheckReply(text=text(language,'check_lookup_failed')+notice,language=language,kind='unavailable',intent_id=context.intent_id,reply_markup={'remove_keyboard':True})

    def render(self,result:CheckResult,language:str,intent_id:str,selected_key:str|None=None)->CheckReply:
        danger=fixed_check_danger(result,language)
        if danger:return CheckReply(text=danger[0],reply_markup=danger[1],kind='danger',language=language,intent_id=intent_id)
        expected=expected_choice(result)
        pieces=[text(language,selected_key if selected_key==expected else expected)]
        rows=sorted(result.observations,key=lambda row:(row.rounded_distance_m,-row.reported_at.timestamp(),row.source))[:5]
        if rows:pieces.append(text(language,'check_showing',shown=str(len(rows)),total=str(len(result.observations))))
        for row in rows:
            source=text(language,'check_shop_report') if row.source=='shop_report' else row.source.upper()
            level=text(language,'check_level_'+row.level) if row.level else text(language,'check_unknown_level')
            pieces.append(text(language,'check_observation',source=source,time=row.reported_at.isoformat(),level=level,distance_m=str(row.rounded_distance_m)))
        if result.district_warnings:pieces.append(text(language,'check_district_showing',shown=str(min(3,len(result.district_warnings))),total=str(len(result.district_warnings))))
        for row in result.district_warnings[:3]:
            pieces.append(text(language,'check_district',district=row.district,state=row.state,time=row.reported_at.isoformat(),level=text(language,'check_level_'+row.level)))
        if result.district_warnings:pieces.append(text(language,'check_district_scope'))
        if result.status!='available':pieces.append(text(language,'check_source_incomplete'))
        links=[]
        for point in result.destinations:
            pieces.append(text(language,'check_destination',name=point.name,type=text(language,'check_destination_'+point.type),date=point.source_date))
            caption=point.name if len(point.name)<=64 else point.name[:63]+'…'
            links.append([{'text':caption,'url':point.destination().route_link}])
        pieces.append(text(language,'check_destination_note'))
        pieces.append(text(language,'check_qualification'))
        if not catalog(language)['_reviewed']:pieces.append(text(language,'translation_notice'))
        rendered='\n'.join(pieces)
        if len(rendered)>4096:
            fallback=[text(language,expected)]
            if result.status!='available':fallback.append(text(language,'check_source_incomplete'))
            if result.district_warnings:fallback.append(text(language,'check_district_scope'))
            fallback.extend((text(language,'check_details_unavailable'),text(language,'check_destination_note'),text(language,'check_qualification')))
            if not catalog(language)['_reviewed']:fallback.append(text(language,'translation_notice'))
            rendered='\n'.join(fallback)
            if len(rendered)>4096:raise ValueError('Static lookup qualifications exceed Telegram limit')
            return CheckReply(text=rendered,language=language,kind='unavailable',intent_id=intent_id,reply_markup={'remove_keyboard':True})
        return CheckReply(text=rendered,language=language,kind='unavailable',intent_id=intent_id,reply_markup={'inline_keyboard':links} if links else {'remove_keyboard':True})

    async def recheck_reply(self,sender:int,reply:InventoryReply,*,registered_flow_waiting:bool=False)->InventoryReply:
        guarded=await self.guard.recheck_reply(sender,reply)
        if guarded.kind=='danger' and not getattr(guarded,'intent_id',None):return guarded # Current registered Danger takes priority.
        if getattr(reply,'intent_id',None):
            current=await asyncio.to_thread(self.intents.active,sender,self.clock())
            if current.intent_id!=reply.intent_id or current.status in ('none','expired'):return await self._reply(sender,'check_expired',language=reply.language)
            if reply.location_request and current.status!='waiting_location':return await self._reply(sender,'check_expired',language=reply.language)
        if getattr(reply,'location_request',False) and registered_flow_waiting:return await self._reply(sender,'check_existing_location',language=reply.language)
        return reply

    async def close(self)->None:
        if self.pending:await asyncio.gather(*tuple(self.pending),return_exceptions=True)
        await self.summarizer.close()
        if self.owns_clients:self.reader.close();self.store.client.close()


def create_public_check_service(settings:Settings)->PublicCheckService:
    from api.tools.firestore import create_firestore_client
    from api.photo_store import PhotoStore
    from api.active_risk import ActiveRiskStore
    from api.public_check_store import FirestoreCheckIntentStore
    from api.public_check import create_public_check_reader
    from api.agents.public_check import CheckSummarizer
    from api.destinations import DestinationLookup
    client=create_firestore_client(settings)
    return PublicCheckService(PhotoStore(client,settings.hash_salt,risks=ActiveRiskStore(client,max_age=settings.official_max_age)),FirestoreCheckIntentStore(client,settings.hash_salt),create_public_check_reader(settings),CheckSummarizer(settings),destinations=DestinationLookup(client,radius_m=settings.destination_search_radius_m),owns_clients=True)

class LazyPublicCheckService:
    def __init__(self,settings:Settings)->None:self.settings=settings;self.active=None
    def _service(self)->PublicCheckService:
        if self.active is None:self.active=create_public_check_service(self.settings)
        return self.active
    async def start(self,sender:int,operation:str,*,registered_flow_waiting:bool=False,language_hint:str|None=None)->InventoryReply:return await self._service().start(sender,operation,registered_flow_waiting=registered_flow_waiting,language_hint=language_hint)
    async def context(self,sender:int,operation:str)->tuple[IntentDecision|None,bool]:return await self._service().context(sender,operation)
    async def lookup(self,sender:int,operation:str,location:CheckLocation,context:IntentDecision)->InventoryReply:return await self._service().lookup(sender,operation,location,context)
    async def recheck_reply(self,sender:int,reply:InventoryReply,*,registered_flow_waiting:bool=False)->InventoryReply:return await self._service().recheck_reply(sender,reply,registered_flow_waiting=registered_flow_waiting)
    async def close(self)->None:
        if self.active:await self.active.close()
