"""Narrow durable event/alert outbox; no external effects inside transactions."""
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4
import json

from google.cloud import firestore
from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import ValidationError

from api.dispatch_models import EventRequest, Shop
from api.demo_scenario import scenario_collection, current_scenario, event_is_current, ScenarioResetBusy


class RequestConflict(ValueError):
    pass


class FirestoreDispatchStore:
    def __init__(self, client: firestore.Client, *, events: str = 'events',
                 alerts: str = 'alerts', shops: str = 'shops') -> None:
        self.client, self.events, self.alerts, self.shops = client, events, alerts, shops
        self.plans, self.deliveries = events+'-plans', alerts+'-delivery'

    def ensure_event(self, request: EventRequest, now: datetime) -> dict:
        event_id = sha256(f'{request.source}:{request.request_id}'.encode()).hexdigest()
        fingerprint = sha256(request.model_dump_json(exclude={'processing_started_at'}).encode()).hexdigest()
        ref = self.client.collection(self.events).document(event_id)
        record = dict(request.model_dump(), event_id=event_id, fingerprint=fingerprint,
                      created_at=now, processing_started_at=request.processing_started_at or now,
                      is_demo=request.source == 'demo' or request.simulation, prepared=False,
                      alert_ids=[], status='pending', pubsub='pending', bigquery='pending')
        @firestore.transactional
        def create(tx):
            existing=ref.get(transaction=tx).to_dict()
            scenario=current_scenario(self.client,scenario_collection(self.shops),tx) if record['is_demo'] else {}
            if existing:
                if existing.get('fingerprint') != fingerprint:
                    facts=request.model_dump(exclude={'processing_started_at'})
                    if any(existing.get(key,EventRequest.model_fields[key].default)!=value for key,value in facts.items()):
                        raise RequestConflict('Request identity was already used for different facts')
                return existing
            if record['is_demo']:
                if scenario.get('state')=='resetting':raise ScenarioResetBusy('Demo reset in progress')
                record['scenario_generation']=scenario.get('generation',0)
            tx.create(ref,record)
            return record
        return create(self.client.transaction())

    def is_current(self,event):
        return event_is_current(event,current_scenario(self.client,scenario_collection(self.shops)))

    def mark_suppressed(self,event_id,reason):
        self.client.collection(self.events).document(event_id).update({'status':'pending','delivery_superseded':True,'suppression_reason':reason})

    def get_event(self, event_id: str) -> dict:
        data = self.client.collection(self.events).document(event_id).get().to_dict()
        if not data:
            raise ValueError('Event not found')
        if data.get('target_plan_ready'):
            plan = self.client.collection(self.plans).document(event_id).get().to_dict()
            if not plan:
                raise RuntimeError('Private dispatch plan missing')
            data['targets'] = plan['targets']
        return data

    def claim(self, event_id: str, now: datetime) -> str | None:
        ref = self.client.collection(self.events).document(event_id)
        owner = uuid4().hex
        @firestore.transactional
        def acquire(tx):
            record = ref.get(transaction=tx).to_dict()
            if record.get('lease_until') and record['lease_until'] > now:
                return None
            tx.update(ref, {'owner': owner, 'lease_until': now+timedelta(seconds=120)})
            return owner
        return acquire(self.client.transaction())

    def update_event(self, event_id: str, owner: str, **fields) -> None:
        ref = self.client.collection(self.events).document(event_id)
        @firestore.transactional
        def update(tx):
            data = ref.get(transaction=tx).to_dict()
            if data.get('owner') != owner:
                raise RuntimeError('Event claim changed')
            values = dict(fields)
            if 'targets' in values:
                tx.set(self.client.collection(self.plans).document(event_id), {'targets': values.pop('targets')})
                values['target_plan_ready'] = True
            tx.update(ref, dict(values, lease_until=datetime.now(UTC)+timedelta(seconds=120)))
        update(self.client.transaction())

    def release(self, event_id: str, owner: str) -> None:
        ref = self.client.collection(self.events).document(event_id)
        @firestore.transactional
        def expire(tx):
            if ref.get(transaction=tx).to_dict().get('owner') == owner:
                tx.update(ref, {'lease_until': datetime.now(UTC)})
        expire(self.client.transaction())

    def target_shops(self) -> list[Shop]:
        shops = []
        scope=current_scenario(self.client,scenario_collection(self.shops)).get('fixture_shop_ids')
        for doc in self.client.collection(self.shops).stream():
            try:
                shop=Shop.model_validate(dict(doc.to_dict(),shop_id=doc.id))
                if shop.is_demo and scope is not None and doc.id not in scope:continue
                shops.append(shop)
            except (ValidationError, TypeError):
                continue
        return shops

    def prepare_alert(self, alert: dict) -> None:
        ref = self.client.collection(self.alerts).document(alert['alert_id'])
        delivery_ref = self.client.collection(self.deliveries).document(alert['alert_id'])
        public_record = {key:value for key,value in alert.items() if key not in ('telegram_chat_id','virtual_recipient')}
        # Firestore rejects array-of-arrays, while Telegram requires that exact
        # inline_keyboard shape. Serialize at rest and restore only on read.
        if public_record.get('reply_markup') is not None:
            public_record['reply_markup'] = json.dumps(public_record['reply_markup'], ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        @firestore.transactional
        def create(tx):
            if ref.get(transaction=tx).exists:
                return
            tx.set(delivery_ref, {key:alert[key] for key in ('telegram_chat_id','virtual_recipient') if key in alert})
            tx.set(ref, public_record)
        create(self.client.transaction())

    def get_alert(self, alert_id: str) -> dict:
        alert = self.client.collection(self.alerts).document(alert_id).get().to_dict()
        delivery = self.client.collection(self.deliveries).document(alert_id).get().to_dict()
        if not alert or not delivery:
            raise RuntimeError('Private alert delivery state missing')
        if isinstance(alert.get('reply_markup'), str):
            markup = json.loads(alert['reply_markup'])
            if not isinstance(markup, dict):
                raise ValueError('Stored Telegram markup must be an object')
            alert['reply_markup'] = markup
        return dict(alert, **delivery)

    def begin_send(self, alert_id: str, event_id: str, owner: str) -> bool:
        ref = self.client.collection(self.alerts).document(alert_id)
        event_ref = self.client.collection(self.events).document(event_id)
        @firestore.transactional
        def begin(tx):
            event = event_ref.get(transaction=tx).to_dict()
            alert = ref.get(transaction=tx).to_dict()
            scenario=current_scenario(self.client,scenario_collection(self.shops),tx) if event.get('is_demo') else {}
            if event.get('owner') != owner:
                raise RuntimeError('Event claim changed')
            if not event_is_current(event,scenario,alert['shop_id']):
                if alert['status'] in ('pending','retryable'):tx.update(ref,{'status':'superseded','suppression_reason':'obsolete_scenario'})
                return False
            if alert['status'] == 'sending':
                # An earlier process may have sent before dying: never blindly resend.
                tx.update(ref, {'status': 'uncertain'})
                return False
            if alert['status'] not in ('pending', 'retryable'):
                return False
            tx.update(ref, {'status': 'sending', 'send_started_at': datetime.now(UTC)})
            tx.update(event_ref, {'lease_until': datetime.now(UTC)+timedelta(seconds=120)})
            return True
        return begin(self.client.transaction())

    def update_alert(self, alert_id: str, event_id: str, owner: str, **fields) -> None:
        event_ref = self.client.collection(self.events).document(event_id)
        alert_ref = self.client.collection(self.alerts).document(alert_id)
        @firestore.transactional
        def update(tx):
            if event_ref.get(transaction=tx).to_dict().get('owner') != owner:
                raise RuntimeError('Event claim changed')
            tx.update(alert_ref, fields)
        update(self.client.transaction())

    def event_alert_ids(self,event_id:str) -> list[str]:
        docs=list(self.client.collection(self.alerts).where(filter=FieldFilter('event_id','==',event_id)).limit(1001).stream(timeout=5,retry=None))
        if len(docs)>1000:raise ValueError('Historical alert scope exceeds bound')
        return [doc.id for doc in docs]

    def pending_event_ids(self, limit: int = 20) -> list[str]:
        return [doc.id for doc in self.client.collection(self.events).where(filter=FieldFilter('status', '==', 'pending')).limit(limit).stream(timeout=5,retry=None)]
