"""Source-bound shop episodes; missing observations never imply recovery."""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4
from typing import Literal

from google.cloud import firestore


@dataclass(frozen=True)
class RiskState:
    episode_id: str | None
    active_danger: bool
    official_danger: bool
    legacy_unknown: bool = False


@dataclass(frozen=True)
class RiskDecision:
    episode_id: str | None
    reason: Literal['accepted','expired','closed_episode','unattributed_source','missing_shop','simulation_mismatch','obsolete_observation','resolved_source_episode','superseded_source_watermark']


class ActiveRiskStore:
    def __init__(self, client, *, risks='active_risks', shops='shops', deliveries='shop_delivery_claims', current_actions='current_vehicle_actions', source_states='official_source_states'):
        self.client,self.risks,self.shops,self.deliveries,self.current_actions=client,risks,shops,deliveries,current_actions
        self.source_states=source_states

    @staticmethod
    def _view(record, shop):
        sources=record.get('sources',{})
        legacy=record.get('legacy_unknown',not record and shop.get('active_danger',False) is not False)
        return RiskState(record.get('episode_id'),legacy or any(s['level']=='danger' for s in sources.values()),
                         any(s['level']=='danger' and s['source'] in ('jps','met') and not s.get('is_demo') for s in sources.values()),legacy)

    def get(self, shop_id):
        record=self.client.collection(self.risks).document(shop_id).get().to_dict() or {}
        shop=self.client.collection(self.shops).document(shop_id).get().to_dict() or {}
        return self._view(record,shop)

    def _source_rejection(self, event, transaction):
        if event['source'] not in ('jps','met') or event['is_demo'] or not event.get('source_key'):return None
        key=event['source_key']
        source=self.client.collection(self.source_states).document(sha256(key.encode()).hexdigest()).get(transaction=transaction).to_dict() or {}
        state=source.get('state')
        if not state:return None
        episode=sha256(f"{key}|{state['started_at'].isoformat()}".encode()).hexdigest()
        ranks={'watch':0,'warning':1,'danger':2}
        if ranks.get(state['highest_level'],-1)>ranks[event['level']]:return 'superseded_source_watermark'
        if state['highest_level'] is None or episode!=event.get('source_episode_id') or (state.get('resolved_at') is not None and state['resolved_at']>=event['source_observed_at']):return 'resolved_source_episode'
        return None

    def apply_event(self, event, shop_id):
        decision=self.apply_event_decision(event,shop_id)
        return decision.episode_id if decision.reason=='accepted' else None

    def apply_event_decision(self, event, shop_id):
        now=datetime.now(UTC)
        observed=event.get('source_observed_at') or event.get('processing_started_at') or event['created_at']
        valid_until=event.get('source_valid_until')
        if observed>now or (valid_until is not None and now>=valid_until):return RiskDecision(None,'expired')
        if event['source'] in ('jps','met') and not event['is_demo'] and (not event.get('source_key') or not event.get('source_episode_id') or not event.get('source_observed_at')):return RiskDecision(None,'unattributed_source')
        if event['source'] in ('jps','met') and not event['is_demo'] and now-observed>timedelta(minutes=90):return RiskDecision(None,'expired')
        if event['source']=='shop_report' and now-observed>timedelta(minutes=30):return RiskDecision(None,'expired')
        reference=self.client.collection(self.risks).document(shop_id)
        shop_ref=self.client.collection(self.shops).document(shop_id)
        @firestore.transactional
        def apply(tx):
            old=reference.get(transaction=tx).to_dict() or {}
            shop=shop_ref.get(transaction=tx).to_dict() or {}
            source_rejection=self._source_rejection(event,tx)
            if source_rejection:return RiskDecision(None,source_rejection)
            if not shop:return RiskDecision(None,'missing_shop')
            if shop.get('is_demo',False)!=event['is_demo']:return RiskDecision(None,'simulation_mismatch')
            if old.get('closed_at') and observed<=old['closed_at']:return RiskDecision(None,'closed_episode')
            sources=dict(old.get('sources',{}))
            key=event.get('source_key') or ('demo:'+event['source'] if event['is_demo'] else 'photo:'+event['event_id'])
            prior=sources.get(key)
            if prior and observed<prior['observed_at']:return RiskDecision(None,'obsolete_observation')
            level=event['level']
            # A new station time gap is not evidence that its old Danger resolved.
            if prior and prior['level']=='danger':level='danger'
            sources[key]={'source':event['source'],'level':level,'observed_at':observed,
                          'source_episode_id':prior['source_episode_id'] if prior and prior['level']=='danger' else event.get('source_episode_id') or event['event_id'],'is_demo':event['is_demo']}
            episode=old.get('episode_id') or sha256(f"{shop_id}:{event['event_id']}".encode()).hexdigest()
            record={**old,'episode_id':episode,'sources':sources,'legacy_unknown':self._view(old,shop).legacy_unknown}
            danger=self._view(record,shop).active_danger
            tx.set(reference,record)
            tx.update(shop_ref,{'active_danger':danger,'active_episode_id':episode})
            return RiskDecision(episode,'accepted')
        return apply(self.client.transaction())

    def recover_official(self, source_key, source_episode_id, observed_at):
        now=datetime.now(UTC)
        if observed_at.tzinfo is None or observed_at>now or now-observed_at>timedelta(minutes=90):return 0
        changed=0
        for doc in self.client.collection(self.risks).stream():
            def predicate(record,shop):
                entry=record.get('sources',{}).get(source_key)
                return bool(entry and not entry.get('is_demo',False) and not shop.get('is_demo',False) and entry['source'] in ('jps','met') and entry['source_episode_id']==source_episode_id and observed_at>=entry['observed_at'])
            changed+=self._recover(doc.id,predicate,lambda entries:{k:v for k,v in entries.items() if k!=source_key},observed_at)
        return changed

    def owner_declared_recovery(self, shop_id, sender_chat_id):
        def allowed(record,shop):
            state=self._view(record,shop)
            return not state.official_danger and not state.legacy_unknown and not shop.get('is_demo',False) and any(r.get('telegram_chat_id')==sender_chat_id and r.get('role')=='owner' for r in shop.get('recipients',[]))
        return bool(self._recover(shop_id,allowed,lambda entries:{k:v for k,v in entries.items() if v['source']!='shop_report'},datetime.now(UTC),provenance='owner_declared'))

    def reset_demo(self, shop_id):
        return bool(self._recover(shop_id,lambda record,shop:shop.get('is_demo') is True,
                                  lambda entries:{k:v for k,v in entries.items() if not v.get('is_demo')},datetime.now(UTC),provenance='operator_demo_reset',clear_legacy=True))

    def _recover(self, shop_id, predicate, remove, at, *, provenance='official',clear_legacy=False):
        ref=self.client.collection(self.risks).document(shop_id);shop_ref=self.client.collection(self.shops).document(shop_id)
        current=self.client.collection(self.current_actions).document(shop_id)
        @firestore.transactional
        def recover(tx):
            record=ref.get(transaction=tx).to_dict() or {};shop=shop_ref.get(transaction=tx).to_dict() or {}
            action=current.get(transaction=tx)
            if not predicate(record,shop):return 0
            sources=remove(record.get('sources',{}))
            updated={**record,'sources':sources,'legacy_unknown':False if clear_legacy else self._view(record,shop).legacy_unknown,
                     'recovery_provenance':provenance,'recovered_at':at}
            if not sources and not updated['legacy_unknown']:updated.update(episode_id=None,closed_at=at)
            danger=self._view(updated,shop).active_danger
            tx.set(ref,updated);tx.update(shop_ref,{'active_danger':danger,'active_episode_id':updated.get('episode_id')})
            if action.exists and not danger:tx.update(current,{'blocked':False,'action_id':None})
            return 1
        return recover(self.client.transaction())

    def claim_delivery(self, shop_id, event):
        """Serialize actual send windows; expired in-flight requests remain ambiguous."""
        ref=self.client.collection(self.deliveries).document(shop_id)
        risk_ref=self.client.collection(self.risks).document(shop_id);shop_ref=self.client.collection(self.shops).document(shop_id)
        now=datetime.now(UTC);owner=uuid4().hex
        @firestore.transactional
        def claim(tx):
            lease=ref.get(transaction=tx).to_dict() or {};risk=risk_ref.get(transaction=tx).to_dict() or {};shop=shop_ref.get(transaction=tx).to_dict() or {}
            source_obsolete=self._source_rejection(event,tx)
            if lease.get('until',now)>now:return 'busy',None
            state=self._view(risk,shop)
            observed=event.get('source_observed_at') or event.get('processing_started_at') or event['created_at']
            expired=(event.get('source_valid_until') is not None and now>=event['source_valid_until']) or (event['source'] in ('jps','met') and not event['is_demo'] and (not event.get('source_observed_at') or now-observed>timedelta(minutes=90))) or (event['source']=='shop_report' and now-observed>timedelta(minutes=30))
            if source_obsolete or expired or (event.get('episode_id') and event['episode_id']!=state.episode_id) or (event['level']!='danger' and state.active_danger):return 'superseded',None
            tx.set(ref,{'owner':owner,'event_id':event['event_id'],'until':now+timedelta(seconds=30)})
            return 'claimed',owner
        return claim(self.client.transaction())

    def release_delivery(self, shop_id, owner):
        ref=self.client.collection(self.deliveries).document(shop_id)
        @firestore.transactional
        def release(tx):
            if (ref.get(transaction=tx).to_dict() or {}).get('owner')==owner:tx.update(ref,{'until':datetime.now(UTC)})
        release(self.client.transaction())
