"""Local durable alert dispatch with explicit per-sink recovery stages."""
import asyncio
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from typing import Callable

from api.alert_composer import AlertComposer, send_alert
from api.agents.sessions import session_user_id
from api.dispatch_models import EventRequest, Shop
from api.dispatch_store import FirestoreDispatchStore
from api.tools.geo import distance_m
from api.tools.telegram import TelegramSendError


class DispatchService:
    def __init__(self, store: FirestoreDispatchStore, telegram, sinks, *, hash_salt: str,
                 composer: AlertComposer | None = None, vehicle_actions=None, active_risk=None, stock_actions=None,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        if not hash_salt:
            raise ValueError('HASH_SALT is required for dispatch')
        self.store, self.telegram, self.sinks = store, telegram, sinks
        self.vehicle_actions = vehicle_actions
        self.active_risk, self.stock_actions = active_risk, stock_actions
        self.hash_salt, self.composer, self.clock = hash_salt, composer or AlertComposer(), clock

    async def process(self, request: EventRequest) -> dict:
        now = self.clock()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('Dispatch clock must be aware')
        event = await asyncio.to_thread(self.store.ensure_event, request, now)
        if self.active_risk is not None and event.get('reporter_shop_id'):
            decision=await asyncio.to_thread(self.active_risk.apply_event_decision,event,event['reporter_shop_id'])
            if decision.reason!='accepted':
                await asyncio.to_thread(self.store.mark_suppressed,event['event_id'],decision.reason)
                return {'event_id':event['event_id'],'status':'superseded','reason':decision.reason}
            if event['level']=='danger' and self.vehicle_actions is not None:
                await asyncio.to_thread(self.vehicle_actions.supersede,event['reporter_shop_id'],event_id=event['event_id'],episode_id=decision.episode_id,at=event['created_at'])
        return await self.resume(event['event_id'])

    async def resume(self, event_id: str) -> dict:
        owner = await asyncio.to_thread(self.store.claim, event_id, self.clock())
        if owner is None:
            return {'event_id': event_id, 'status': 'busy'}
        try:
            event = await asyncio.to_thread(self.store.get_event, event_id)
            if not event['prepared']:
                if 'targets' not in event:
                    shops = await asyncio.to_thread(self.store.target_shops)
                    targets = []
                    for shop in shops:
                        # Simulations have an absolute recipient boundary; real events do not target demos.
                        if shop.shop_id == event.get('reporter_shop_id'):
                            continue
                        if shop.is_demo != event['is_demo']:
                            continue
                        distance = distance_m(event['lat'], event['lng'], shop.lat, shop.lng)
                        if distance <= event['radius_m']:
                            targets.append(dict(shop.model_dump(), distance_m=distance))
                    await asyncio.to_thread(self.store.update_event, event_id, owner, targets=targets)
                    event['targets'] = targets
                if self.active_risk is not None:
                    eligible=[]
                    suppressed=[]
                    for raw in event['targets']:
                        decision=await asyncio.to_thread(self.active_risk.apply_event_decision,event,raw['shop_id'])
                        if decision.reason=='accepted':eligible.append(dict(raw,episode_id=decision.episode_id))
                        else:suppressed.append({'shop_id':raw['shop_id'],'reason':decision.reason})
                    event['targets']=eligible
                    await asyncio.to_thread(self.store.update_event,event_id,owner,targets=eligible,suppressed_targets=suppressed)
                target_shops = [Shop.model_validate(raw) for raw in event['targets']]
                await self.composer.prepare(event, {r.language for shop in target_shops for r in shop.recipients},
                                            has_inventory=any(shop.baseline_inventory_id for shop in target_shops),
                                            has_vehicle=any(shop.has_vehicle for shop in target_shops))
                ids = []
                for raw in event['targets']:
                    shop = Shop.model_validate(raw)
                    shop_event={**event,'episode_id':raw.get('episode_id') or event.get('episode_id')}
                    snapshot = await self.composer.action_snapshot(shop_event, shop)
                    if self.vehicle_actions is not None and event['level'] == 'danger':
                        await asyncio.to_thread(self.vehicle_actions.supersede, shop.shop_id, event_id=event_id, episode_id=shop_event.get('episode_id') or event_id, at=event['created_at'])
                    from api.vehicle_confirmations import vehicle_action_id
                    snapshot=snapshot.model_copy(update={
                        'episode_id':shop_event.get('episode_id'),
                        'vehicle_action_id':vehicle_action_id(event_id,shop.shop_id) if snapshot.vehicle_type and self.vehicle_actions is not None else snapshot.vehicle_action_id,
                        'stock_action_id':sha256(f'{event_id}:{shop.shop_id}:stock'.encode()).hexdigest()[:32] if snapshot.items and self.stock_actions is not None else snapshot.stock_action_id})
                    action_enabled = True
                    if self.vehicle_actions is not None and event['level'] == 'warning' and snapshot.vehicle_type:
                        action = await asyncio.to_thread(self.vehicle_actions.prepare, shop_event, shop, snapshot, self.hash_salt)
                        from api.dispatch_models import ActionSnapshot
                        snapshot = ActionSnapshot.model_validate(action['snapshot'])
                        action_enabled = action['state'] == 'active'
                    if self.stock_actions is not None and event['level']=='warning' and snapshot.items:
                        action=await asyncio.to_thread(self.stock_actions.prepare,shop_event,shop,snapshot,self.hash_salt)
                        from api.dispatch_models import ActionSnapshot
                        snapshot=ActionSnapshot.model_validate(action['snapshot'])
                    for recipient in shop.recipients:
                        recipient_hash = session_user_id(recipient.telegram_chat_id, self.hash_salt)
                        alert_id = sha256(f'{event_id}:{shop.shop_id}:{recipient_hash}'.encode()).hexdigest()
                        text, snapshot, markup = await self.composer.compose(shop_event, shop, recipient.language, snapshot_override=snapshot, vehicle_action_enabled=action_enabled)
                        alert = dict(
                            alert_id=alert_id, event_id=event_id, shop_id=shop.shop_id, episode_id=shop_event.get('episode_id'),
                            telegram_chat_id=recipient.telegram_chat_id, telegram_chat_id_hash=recipient_hash,
                            level=event['level'], language=recipient.language, is_demo=event['is_demo'],
                            text=text, snapshot=snapshot.model_dump(mode='json'), reply_markup=markup,
                            created_at=event['created_at'], distance_m=raw['distance_m'],
                            status='pending', bigquery='pending', sent_at=None,
                        )
                        await asyncio.to_thread(self.store.prepare_alert, alert)
                        ids.append(alert_id)
                        await asyncio.to_thread(self.store.update_event, event_id, owner)
                await asyncio.to_thread(self.store.update_event, event_id, owner, prepared=True, alert_ids=ids)
                event['alert_ids'] = ids
            # Telegram comes before optional analytics/publish calls: sink failures cannot suppress Danger.
            for alert_id in event['alert_ids']:
                alert=await asyncio.to_thread(self.store.get_alert,alert_id)
                delivery_owner=None
                if self.active_risk is not None:
                    disposition,delivery_owner=await asyncio.to_thread(self.active_risk.claim_delivery,alert['shop_id'],{**event,'episode_id':alert.get('episode_id')})
                    if disposition=='busy':continue
                    if disposition=='superseded':
                        if alert['status'] in ('pending','retryable'):
                            await asyncio.to_thread(self.store.update_alert,alert_id,event_id,owner,status='superseded',suppression_reason='active_risk_or_expired_episode',bigquery='done')
                        continue
                try:
                    if await asyncio.to_thread(self.store.begin_send,alert_id,event_id,owner):
                        try:
                            message_id=await asyncio.to_thread(send_alert,self.telegram,alert)
                        except TelegramSendError as error:
                            await asyncio.to_thread(self.store.update_alert,alert_id,event_id,owner,status='uncertain' if error.uncertain else 'retryable')
                        except Exception:
                            await asyncio.to_thread(self.store.update_alert,alert_id,event_id,owner,status='uncertain')
                        else:
                            sent_at=self.clock()
                            await asyncio.to_thread(self.store.update_alert,alert_id,event_id,owner,status='accepted',message_id=message_id,sent_at=sent_at,
                                                    latency_ms=max(0,int((sent_at-(event.get('processing_started_at') or event['created_at'])).total_seconds()*1000)))
                finally:
                    if delivery_owner is not None:
                        await asyncio.to_thread(self.active_risk.release_delivery,alert['shop_id'],delivery_owner)
            event = await asyncio.to_thread(self.store.get_event, event_id)
            for stage, action in [('pubsub', self.sinks.publish_event), ('bigquery', self.sinks.insert_event)]:
                if event[stage] != 'done':
                    try:
                        await asyncio.to_thread(action, event)
                    except Exception:
                        # Keep durable pending progress; external sink outcome may be ambiguous.
                        pass
                    else:
                        await asyncio.to_thread(self.store.update_event, event_id, owner, **{stage: 'done'})
            counts = Counter()
            pending = False
            for alert_id in event['alert_ids']:
                alert = await asyncio.to_thread(self.store.get_alert, alert_id)
                counts[alert['status']] += 1
                if alert['status'] in ('accepted', 'uncertain') and alert['bigquery'] != 'done':
                    try:
                        await asyncio.to_thread(self.sinks.insert_alert, alert)
                    except Exception:
                        pass
                    else:
                        await asyncio.to_thread(self.store.update_alert, alert_id, event_id, owner, bigquery='done')
                        alert['bigquery'] = 'done'
                if alert['status'] in ('pending', 'sending', 'retryable') or alert['bigquery'] != 'done':
                    pending = True
            latest = await asyncio.to_thread(self.store.get_event, event_id)
            pending |= latest['pubsub'] != 'done' or latest['bigquery'] != 'done'
            status = 'pending' if pending else ('needs_review' if counts.get('uncertain') else 'complete')
            await asyncio.to_thread(self.store.update_event, event_id, owner, status=status)
            # No chat IDs, recipient hashes, private snapshots or message bodies leave this boundary.
            return {'event_id': event_id, 'status': status, 'alerts': dict(counts)}
        finally:
            await asyncio.to_thread(self.store.release, event_id, owner)

    async def close(self) -> None:
        if self.composer.selector is not None and hasattr(self.composer.selector, 'close'):
            await self.composer.selector.close()
        if hasattr(self.sinks, 'close'):
            await asyncio.to_thread(self.sinks.close)
        if hasattr(self.store, 'client'):
            self.store.client.close()

    async def resume_pending(self, limit: int = 20) -> list[dict]:
        ids = await asyncio.to_thread(self.store.pending_event_ids, limit)
        return [await self.resume(event_id) for event_id in ids]


def create_dispatch_service(settings) -> DispatchService:
    from api.tools.cloud_events import create_event_sinks
    from api.tools.firestore import create_firestore_client
    from api.tools.telegram import TelegramAPI
    from api.agents.warning_selector import WarningSelector
    from api.destinations import DestinationLookup
    from api.vehicle_confirmations import VehicleActionStore
    from api.active_risk import ActiveRiskStore
    from api.stock_confirmations import StockActionStore
    client = create_firestore_client(settings)
    composer = AlertComposer(selector=WarningSelector(settings), destinations=DestinationLookup(client, radius_m=settings.destination_search_radius_m),
                             vehicle_minutes=settings.vehicle_action_target_minutes,
                             stock_minutes=settings.stock_action_target_minutes)
    return DispatchService(FirestoreDispatchStore(client),
                           TelegramAPI(settings.telegram_bot_token), create_event_sinks(settings),
                           hash_salt=settings.hash_salt, composer=composer, vehicle_actions=VehicleActionStore(client), active_risk=ActiveRiskStore(client,max_age=settings.official_max_age), stock_actions=StockActionStore(client))
