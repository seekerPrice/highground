"""Recipient-bound immutable actions and self-reported completion outbox."""
import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any, Literal
from uuid import uuid4

from google.cloud import firestore

from api.agents.sessions import session_user_id
from api.dispatch_models import ActionSnapshot, Shop

ConfirmationStatus = Literal['recorded', 'already_recorded', 'unavailable', 'superseded']


def vehicle_action_id(event_id: str, shop_id: str) -> str:
    return sha256(f'{event_id}:{shop_id}:vehicle'.encode()).hexdigest()[:32]


class VehicleActionStore:
    def __init__(self, client: firestore.Client, *, actions: str = 'vehicle_actions',
                 current: str = 'current_vehicle_actions', confirmations: str = 'confirmations',
                 alerts: str = 'alerts', shops: str = 'shops') -> None:
        self.client = client
        self.actions, self.current, self.confirmations = actions, current, confirmations
        self.alerts, self.shops = alerts, shops

    def get(self, action_id: str) -> dict[str, Any] | None:
        return self.client.collection(self.actions).document(action_id).get().to_dict()

    def prepare(self, event: dict[str, Any], shop: Shop, snapshot: ActionSnapshot, hash_salt: str) -> dict[str, Any]:
        action_id = vehicle_action_id(event['event_id'], shop.shop_id)
        reference = self.client.collection(self.actions).document(action_id)
        current_ref = self.client.collection(self.current).document(shop.shop_id)
        scoped_episode = event.get('episode_id') or event['event_id']
        frozen = snapshot.model_copy(update={'vehicle_action_id': action_id, 'episode_id': scoped_episode})
        record = {
            'action_id': action_id, 'event_id': event['event_id'], 'shop_id': shop.shop_id,
            'episode_id': scoped_episode, 'kind': 'vehicle', 'snapshot': frozen.model_dump(mode='json'),
            'recipient_hashes': [session_user_id(r.telegram_chat_id, hash_salt) for r in shop.recipients],
            'is_demo': event['is_demo'], 'created_at': event['created_at'], 'state': 'active',
        }

        @firestore.transactional
        def save(transaction: firestore.Transaction) -> dict[str, Any]:
            existing = reference.get(transaction=transaction)
            current = current_ref.get(transaction=transaction).to_dict() or {}
            if existing.exists:
                return existing.to_dict()
            old_ref = self.client.collection(self.actions).document(current['action_id']) if current.get('action_id') else None
            old = old_ref.get(transaction=transaction) if old_ref else None
            newer = not current or (event['created_at'], event['event_id']) >= (current['created_at'], current['event_id'])
            if current.get('blocked') or not newer:
                record['state'] = 'superseded'
            else:
                if old and old.exists:
                    transaction.update(old_ref, {'state': 'superseded', 'superseded_by': event['event_id']})
                transaction.set(current_ref, {'action_id': action_id, 'event_id': event['event_id'],
                                             'episode_id': scoped_episode, 'created_at': event['created_at'], 'blocked': False})
            transaction.create(reference, record)
            return record
        return save(self.client.transaction())

    def supersede(self, shop_id: str, *, event_id: str, episode_id: str, at: datetime) -> None:
        """Task 10 invokes this before applicable Danger, not after delivery.

        A new Warning never clears this guard; explicit recovery/new-episode
        handling owns releasing it. This function does not infer flood recovery.
        """
        current_ref = self.client.collection(self.current).document(shop_id)
        shop_ref = self.client.collection(self.shops).document(shop_id)
        @firestore.transactional
        def invalidate(transaction: firestore.Transaction) -> None:
            current = current_ref.get(transaction=transaction).to_dict() or {}
            reference = self.client.collection(self.actions).document(current['action_id']) if current.get('action_id') else None
            action = reference.get(transaction=transaction) if reference else None
            if action and action.exists:
                transaction.update(reference, {'state': 'superseded', 'superseded_by': event_id})
            transaction.update(shop_ref, {'active_danger': True})
            transaction.set(current_ref, {'event_id': event_id, 'episode_id': episode_id,
                                         'created_at': at, 'blocked': True})
        invalidate(self.client.transaction())

    def record(self, action_id: str, *, sender_chat_id: int, message_chat_id: int, message_id: int,
               sender_hash: str, now: datetime) -> tuple[ConfirmationStatus, str, str | None]:
        action_ref = self.client.collection(self.actions).document(action_id)
        confirmation_ref = self.client.collection(self.confirmations).document(action_id)

        @firestore.transactional
        def confirm(transaction: firestore.Transaction) -> tuple[ConfirmationStatus, str, str | None]:
            action = action_ref.get(transaction=transaction).to_dict() or {}
            if not action or sender_chat_id != message_chat_id or sender_hash not in action.get('recipient_hashes', []):
                return 'unavailable', 'en', None
            shop_ref = self.client.collection(self.shops).document(action['shop_id'])
            current_ref = self.client.collection(self.current).document(action['shop_id'])
            alert_id = sha256(f"{action['event_id']}:{action['shop_id']}:{sender_hash}".encode()).hexdigest()
            alert_ref = self.client.collection(self.alerts).document(alert_id)
            shop = shop_ref.get(transaction=transaction).to_dict() or {}
            current = current_ref.get(transaction=transaction).to_dict() or {}
            alert = alert_ref.get(transaction=transaction).to_dict() or {}
            existing = confirmation_ref.get(transaction=transaction)
            recipient = next((r for r in shop.get('recipients', []) if r.get('telegram_chat_id') == sender_chat_id and r.get('role') in ('owner', 'worker')), None)
            if not recipient or not alert or alert.get('message_id') != message_id or alert.get('status') != 'accepted':
                return 'unavailable', 'en', None
            language = recipient.get('language', 'en')
            if action['state'] != 'active' or current.get('blocked') or current.get('action_id') != action_id or shop.get('active_danger', False) is not False:
                return 'superseded', language, None
            snapshot = ActionSnapshot.model_validate(action['snapshot'])
            alert_snapshot = ActionSnapshot.model_validate(alert['snapshot'])
            if action['kind'] != 'vehicle' or alert.get('level') != 'warning' or alert_snapshot != snapshot or alert_snapshot.vehicle_action_id != action_id or not snapshot.vehicle_type or snapshot.vehicle_target_at is None:
                return 'unavailable', language, None
            if existing.exists:
                return 'already_recorded', language, action_id
            transaction.create(confirmation_ref, {
                'confirmation_id': action_id, 'action_id': action_id, 'episode_id': action['episode_id'],
                'event_id': action['event_id'], 'alert_id': alert_id, 'shop_id': action['shop_id'],
                'kind': 'vehicle', 'protected_value_rm': None, 'confirmed_at': now,
                'is_demo': action['is_demo'], 'self_reported': True,
                'confirmed_by_hash': sender_hash, 'snapshot': action['snapshot'], 'bigquery': 'pending',
            })
            return 'recorded', language, action_id
        return confirm(self.client.transaction())

    def claim_sink(self, confirmation_id: str, now: datetime) -> tuple[str, dict[str, Any]] | None:
        ref = self.client.collection(self.confirmations).document(confirmation_id)
        owner = uuid4().hex
        @firestore.transactional
        def acquire(transaction: firestore.Transaction):
            record = ref.get(transaction=transaction).to_dict() or {}
            if not record or record['bigquery'] == 'done' or record.get('sink_lease_until', now) > now:
                return None
            transaction.update(ref, {'sink_owner': owner, 'sink_lease_until': now + timedelta(seconds=30)})
            return owner, record
        return acquire(self.client.transaction())

    def finish_sink(self, confirmation_id: str, owner: str, *, succeeded: bool) -> None:
        ref = self.client.collection(self.confirmations).document(confirmation_id)
        @firestore.transactional
        def finish(transaction: firestore.Transaction) -> None:
            record = ref.get(transaction=transaction).to_dict() or {}
            if record.get('sink_owner') != owner:
                return
            transaction.update(ref, {'bigquery': 'done' if succeeded else 'pending', 'sink_lease_until': datetime.now(UTC)})
        finish(self.client.transaction())


class VehicleConfirmationService:
    def __init__(self, store: VehicleActionStore, sinks, *, hash_salt: str) -> None:
        self.store, self.sinks, self.hash_salt = store, sinks, hash_salt

    async def record(self, action_id: str, *, sender_chat_id: int, message_chat_id: int, message_id: int) -> tuple[ConfirmationStatus, str, str | None]:
        identity = session_user_id(sender_chat_id, self.hash_salt)
        return await asyncio.to_thread(self.store.record, action_id, sender_chat_id=sender_chat_id,
                                       message_chat_id=message_chat_id, message_id=message_id,
                                       sender_hash=identity, now=datetime.now(UTC))

    async def flush(self, confirmation_id: str) -> None:
        try:
            claimed = await asyncio.to_thread(self.store.claim_sink, confirmation_id, datetime.now(UTC))
        except Exception:
            # Analytics is optional after the durable domain confirmation. A
            # failed claim leaves its pending record for a later bounded resume.
            return
        if claimed is None:
            return
        owner, record = claimed
        succeeded = False
        try:
            await asyncio.to_thread(self.sinks.insert_confirmation, record)
            succeeded = True
        except Exception:
            pass  # Pending outbox remains recoverable; never count physical rows.
        finally:
            try:
                await asyncio.to_thread(self.store.finish_sink, confirmation_id, owner, succeeded=succeeded)
            except Exception:
                # Preserve the lease on ambiguous completion. Resume may retry
                # after expiry; aggregates dedupe the immutable logical ID.
                pass

    async def resume_pending(self, limit: int = 20) -> None:
        from google.cloud.firestore_v1.base_query import FieldFilter
        ids = await asyncio.to_thread(lambda: [doc.id for doc in self.store.client.collection(self.store.confirmations).where(filter=FieldFilter('bigquery', '==', 'pending')).limit(limit).stream()])
        for identity in ids:
            await self.flush(identity)
