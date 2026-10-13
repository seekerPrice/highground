"""Private, atomic episode provenance and bounded trusted history projection."""
from hashlib import sha256
import time
from api.calibration import geohash6


def history_key(shop_id,episode_id,is_demo,generation):
    return sha256(f'{is_demo}:{generation}:{shop_id}:{episode_id}'.encode()).hexdigest()


def risk_history_writes(client,collection,tx,shop_id,shop,previous,updated,*,event=None,observed=None):
    """Read before any writes. A legacy open episode has no invented start."""
    if collection is None:return ()
    is_demo=shop.get('is_demo',False)
    previous_id=previous.get('episode_id');next_id=updated.get('episode_id')
    writes=[]
    if previous_id:
        generation=previous.get('scenario_generation') if is_demo else None
        ref=client.collection(collection).document(history_key(shop_id,previous_id,is_demo,generation))
        row=ref.get(transaction=tx).to_dict() or {}
        if row and previous_id!=next_id and updated.get('closed_at') is not None and row.get('closed_at') is None:
            writes.append((ref,{**row,'closed_at':updated['closed_at'],'closure_basis':updated.get('recovery_provenance','official')}))
    if next_id and not previous_id:
        generation=updated.get('scenario_generation') if is_demo else None
        if is_demo and type(generation) is not int:raise ValueError('Confirmed demo generation required')
        ref=client.collection(collection).document(history_key(shop_id,next_id,is_demo,generation))
        existing=ref.get(transaction=tx).to_dict() or {}
        if not existing:
            if event is None or observed is None:raise ValueError('Confirmed episode start required')
            writes.append((ref,{'shop_id':shop_id,'episode_id':next_id,'area':geohash6(shop['lat'],shop['lng']),
                'started_at':observed,'start_basis':'source_observation' if event.get('source_observed_at') else 'receipt_time',
                'first_event_id':event['event_id'],'is_demo':is_demo,'scenario_generation':generation,
                'closed_at':None,'closure_basis':None,'history_status':'complete'}))
    return tuple(writes)


class OutcomeHistoryAdapter:
    def __init__(self,client,outcome_store,risks,*,events='events',alerts='alerts',ledger='risk_episode_history'):
        self.client,self.store,self.risks,self.events,self.alerts,self.ledger=client,outcome_store,risks,events,alerts,ledger

    @staticmethod
    def _deadline(deadline):
        if deadline is not None and time.monotonic()>=deadline:raise TimeoutError("Outcome work budget elapsed")

    def _scope(self,deadline=None):
        from api.demo_scenario import current_scenario,scenario_collection
        self._deadline(deadline)
        return current_scenario(self.client,scenario_collection(self.store.shops))

    @staticmethod
    def _current(row,scenario):
        return not row['is_demo'] or (scenario.get('state','ready')=='ready' and row['scenario_generation']==scenario.get('generation',0) and (scenario.get('fixture_shop_ids') is None or row['shop_id'] in scenario['fixture_shop_ids']))

    def _rows(self,deadline=None):
        from google.cloud.firestore_v1.base_query import FieldFilter
        scenario=self._scope(deadline)
        self._deadline(deadline)
        real=self.client.collection(self.ledger).where(filter=FieldFilter('is_demo','==',False))
        rows=list(real.limit(1001).stream(timeout=5,retry=None))
        if scenario.get('state','ready')=='ready':
            self._deadline(deadline)
            demo=self.client.collection(self.ledger).where(filter=FieldFilter('is_demo','==',True)).where(filter=FieldFilter('scenario_generation','==',scenario.get('generation',0)))
            rows.extend(demo.limit(1001).stream(timeout=5,retry=None))
        if len(rows)>1000:raise ValueError('Trusted episode history overflow; scope unavailable')
        return rows

    def project(self,row,*,deadline=None):
        self._deadline(deadline)
        from google.cloud.firestore_v1.base_query import FieldFilter
        from api.outcome_models import OutcomeEpisode,OutcomeDelivery
        from api.agents.sessions import session_user_id
        if row.get('history_status')!='complete':raise ValueError('Trusted episode start unavailable')
        query=self.client.collection(self.alerts).where(filter=FieldFilter('shop_id','==',row['shop_id'])).where(filter=FieldFilter('episode_id','==',row['episode_id']))
        alerts=list(query.limit(1001).stream(timeout=5,retry=None));deliveries=[]
        overflow=len(alerts)>1000
        for doc in alerts[:1000]:
            self._deadline(deadline)
            alert=doc.to_dict()
            if alert.get('is_demo',False)!=row['is_demo'] or (row['is_demo'] and alert.get('scenario_generation',0)!=row['scenario_generation']):continue
            event=self.client.collection(self.events).document(alert['event_id']).get(timeout=5,retry=None).to_dict() or {}
            if not event:raise ValueError('Delivery source history unavailable')
            deliveries.append(OutcomeDelivery(alert_id=doc.id,created_at=alert['created_at'],request_started_at=alert.get('send_started_at'),
                accepted_at=alert.get('sent_at') if alert['status']=='accepted' else None,simulated_at=alert.get('sent_at') if alert['status']=='simulated' else None,
                status=alert['status'],source=event['source'],level=alert['level'],provenance=alert.get('delivery_provenance','telegram_api')))
        self._deadline(deadline)
        shop=self.client.collection(self.store.shops).document(row['shop_id']).get(timeout=5,retry=None).to_dict() or {}
        if row.get('fixture_deliveries_json') is not None:
            from pydantic import TypeAdapter
            from api.demo_scenario import SHOP_IDS,FIXTURE_ORIGIN,current_scenario,scenario_collection
            self._deadline(deadline)
            scenario=current_scenario(self.client,scenario_collection(self.store.shops))
            if row.get('start_basis')!='synthetic_fixture' or row.get('fixture_origin')!='task22_synthetic_history_v1' or not row['is_demo'] or row['shop_id'] not in SHOP_IDS or shop.get('is_demo') is not True or shop.get('fixture_origin')!=FIXTURE_ORIGIN or scenario.get('state','ready')!='ready' or scenario.get('generation',0)!=row['scenario_generation']:raise ValueError('Untrusted fixture history')
            fixture=TypeAdapter(tuple[OutcomeDelivery,...]).validate_json(row['fixture_deliveries_json'])
            if len(fixture)>1000 or any(d.provenance!='synthetic_fixture' or d.status!='simulated' or d.source!='demo' for d in fixture):raise ValueError('Invalid fixture delivery provenance')
            deliveries.extend(fixture)
            if len(deliveries)>1000:raise ValueError('Fixture delivery history overflow')
        owners=[r for r in shop.get('recipients',[]) if r.get('role')=='owner' and type(r.get('telegram_chat_id')) is int]
        return OutcomeEpisode(shop_id=row['shop_id'],episode_id=row['episode_id'],area=row['area'],started_at=row['started_at'],closed_at=row['closed_at'],
            owner_hash=session_user_id(owners[0]['telegram_chat_id'],self.store.salt) if len(owners)==1 else None,
            is_demo=row['is_demo'],scenario_generation=row['scenario_generation'],deliveries=tuple(deliveries),history_status='overflowed' if overflow else 'complete')

    def refresh(self,*,limit=20,now,deadline=None):
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Invalid history work budget')
        # Oldest refreshed first rotates this bounded work budget across the full
        # scope; it is never a sample used to calculate a response ratio.
        scenario=self._scope(deadline)
        rows=sorted((doc for doc in self._rows(deadline) if self._current(doc.to_dict(),scenario)),key=lambda doc:(doc.to_dict().get('projected_at') or doc.to_dict()['started_at'],doc.id))
        keys=[]
        for doc in rows[:limit]:
            self._deadline(deadline)
            episode=self.project(doc.to_dict(),deadline=deadline)
            self._deadline(deadline)
            key=self.store.register_episode(episode)
            self._deadline(deadline)
            doc.reference.update({'projected_at':now},timeout=5,retry=None)
            keys.append(key)
        return tuple(keys)

    def calibration_batches(self,*,now,deadline=None):
        """Complete relevant area/window batches, never first-N responses."""
        from datetime import timedelta
        from google.cloud.firestore_v1.base_query import FieldFilter
        from api.outcome_models import OwnerOutcome,CalibrationEvidence
        from api.outcome_store import episode_key
        self._deadline(deadline)
        records=list(self.client.collection(self.store.prefix+'outcome_responses').where(filter=FieldFilter('created_at','>=',now-timedelta(days=30))).limit(1001).stream(timeout=5,retry=None))
        if len(records)>1000:raise ValueError('Calibration response scope overflow')
        scenario=self._scope(deadline)
        ledger={doc.id:doc.to_dict() for doc in self._rows(deadline) if self._current(doc.to_dict(),scenario)};batches={}
        for doc in records:
            self._deadline(deadline)
            response=OwnerOutcome.model_validate_json(doc.to_dict()['json'])
            if response.answered_at>now or not self._current(response.model_dump(),scenario):continue
            scope=(response.area,response.is_demo,response.scenario_generation)
            batches.setdefault(scope,[]).append(response)
        result={};overflow=[]
        for scope,responses in batches.items():
            if len(responses)>100:overflow.append(scope);continue
            evidence=[]
            for response in responses:
                self._deadline(deadline)
                key=history_key(response.shop_id,response.episode_id,response.is_demo,response.scenario_generation)
                if key not in ledger:raise ValueError('Calibration requires trusted complete episode history')
                episode=self.project(ledger[key],deadline=deadline)
                self._deadline(deadline)
                self.store.register_episode(episode)
                evidence.append(CalibrationEvidence(episode=episode,response=response))
            result[scope]=tuple(evidence)
        return result,tuple(overflow)

    def radius_plan(self,shop,event):
        from api.calibration import freeze_radius
        area=geohash6(shop.lat,shop.lng);generation=event.get('scenario_generation',0) if shop.is_demo else None
        state=None
        if event['source'] in ('shop_report','demo') and event['level']=='warning':
            try:
                state=self.store.calibration_state(area,is_demo=shop.is_demo,generation=generation)
            except Exception:
                # Optional learning failure retains the configured base radius,
                # never claims a learned version or blocks authoritative Danger.
                state=None
        return freeze_radius(event['radius_m'],level=event['level'],source=event['source'],area=area,is_demo=shop.is_demo,scenario_generation=generation,state=state)
