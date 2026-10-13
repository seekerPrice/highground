"""Six labelled historical episodes of one existing synthetic shop, never accuracy."""
import argparse
from datetime import UTC,datetime,timedelta
from hashlib import sha256
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from google.cloud import firestore
from pydantic import TypeAdapter
from api.calibration import geohash6
from api.config import load_settings
from api.demo_scenario import FIXTURE_ORIGIN,SHOP_IDS,scenario_collection
from api.outcome_models import OutcomeEpisode,OutcomeDelivery,OwnerOutcome,CalibrationEvidence,CalibrationState
from api.outcome_store import FirestoreOutcomeStore,episode_key
from api.outcome_analytics import OutcomeAnalytics
from api.tools.emulators import loopback_endpoint

ORIGIN='task22_synthetic_history_v1'

def require_local(settings,environment)->None:
    if not settings.local_development or not settings.demo_mode or not settings.gcp_project:raise ValueError('Explicit local demo/project required')
    for key,http in (('FIRESTORE_EMULATOR_HOST',False),('PUBSUB_EMULATOR_HOST',False),('STORAGE_EMULATOR_HOST',True),('BIGQUERY_EMULATOR_HOST',True)):
        loopback_endpoint(environment.get(key,''),http=http)

def fixture_plan(shop:dict,generation:int,anchor:datetime)->tuple[CalibrationEvidence,...]:
    if shop.get('shop_id') not in SHOP_IDS or shop.get('fixture_origin')!=FIXTURE_ORIGIN or shop.get('is_demo') is not True:raise ValueError('Owned fixture shop required')
    area=geohash6(shop['lat'],shop['lng']);owner=sha256(f'{ORIGIN}:{generation}:{shop["shop_id"]}:synthetic-owner'.encode()).hexdigest();result=[]
    for i in range(6):
        started=anchor-timedelta(days=8-i) if i<5 else anchor-timedelta(hours=12)
        closed=started+timedelta(hours=6 if i<5 else 1)
        deliveries=(OutcomeDelivery(alert_id=sha256(f'{ORIGIN}:{generation}:{i}:simulated'.encode()).hexdigest(),created_at=started,simulated_at=started+timedelta(minutes=1),level='warning',source='demo',status='simulated',provenance='synthetic_fixture'),) if i<5 else ()
        ep=OutcomeEpisode(shop_id=shop['shop_id'],episode_id=f'{ORIGIN}-g{generation}-{i}',area=area,owner_hash=owner,started_at=started,closed_at=closed,is_demo=True,scenario_generation=generation,deliveries=deliveries)
        response=OwnerOutcome(response_id=episode_key(ep),shop_id=ep.shop_id,episode_id=ep.episode_id,area=area,owner_hash=owner,answer='no' if i<5 else 'inside',observed_at=closed,answered_at=closed+timedelta(minutes=1),entrypoint='alert_response' if i<5 else 'owner_report',origin='synthetic_fixture',is_demo=True,scenario_generation=generation)
        result.append(CalibrationEvidence(episode=ep,response=response))
    return tuple(result)

class OutcomeFixtureSeeder:
    def __init__(self,store:FirestoreOutcomeStore,analytics:OutcomeAnalytics,*,ledger='risk_episode_history'):
        self.store,self.analytics,self.ledger=store,analytics,ledger
    def _scope(self,tx,generation=None):
        store=self.store;scenario=store._read(store.client.collection(scenario_collection(store.shops)).document('current'),tx)
        shops=[store._read(store.client.collection(store.shops).document(identity),tx) for identity in SHOP_IDS]
        current=scenario.get('generation')
        if scenario.get('state')!='ready' or type(current) is not int or current<0 or (generation is not None and current!=generation):raise ValueError('Ready current generation required')
        if scenario.get('fixture_shop_ids') is not None and set(scenario['fixture_shop_ids'])!=set(SHOP_IDS):raise ValueError('Exact six fixture bindings required')
        if any(s.get('shop_id')!=identity or s.get('is_demo') is not True or s.get('fixture_origin')!=FIXTURE_ORIGIN for s,identity in zip(shops,SHOP_IDS)):raise ValueError('All six owned synthetic shops must already exist')
        return current,shops
    def seed(self,*,now:datetime)->dict:
        self.store._clock(now);store=self.store
        @firestore.transactional
        def reserve(tx):
            generation,shops=self._scope(tx);manifest=store._ref('seed',f'{ORIGIN}-{generation}');old=store._read(manifest,tx)
            existing=store.calibration_state(geohash6(shops[0]["lat"],shops[0]["lng"]),is_demo=True,generation=generation,transaction=tx)
            if old:return generation,shops[0],old['anchor']
            if existing:raise ValueError('Existing calibration cannot be replaced by historical fixture')
            tx.create(manifest,{'anchor':now,'fixture_origin':ORIGIN,'generation':generation})
            return generation,shops[0],now
        generation,shop,anchor=reserve(store.client.transaction(max_attempts=5));batch=fixture_plan(shop,generation,anchor)
        for evidence in batch:
            ep,response=evidence.episode,evidence.response;key=store.register_episode(ep)
            ledger_ref=store.client.collection(self.ledger).document(key)
            ledger=dict(shop_id=ep.shop_id,episode_id=ep.episode_id,area=ep.area,started_at=ep.started_at,closed_at=ep.closed_at,is_demo=True,scenario_generation=generation,start_basis='synthetic_fixture',closure_basis='synthetic_fixture',fixture_origin=ORIGIN,fixture_deliveries_json=TypeAdapter(tuple[OutcomeDelivery,...]).dump_json(ep.deliveries).decode(),history_status='complete')
            records=[(ledger_ref,ledger),(store._ref('responses',key),{'json':response.model_dump_json(),'created_at':response.answered_at}),(store._ref('facts',key),{'json':response.model_dump_json(),'bigquery':'pending'})]
            if ep.deliveries:records.append((store._ref('prompts',key),{'status':'simulated','provenance':'synthetic_fixture','is_demo':True,'scenario_generation':generation,'fixture_origin':ORIGIN}))
            @firestore.transactional
            def write(tx):
                self._scope(tx,generation);previous=[store._read(ref,tx) for ref,_ in records]
                for (_,value),old in zip(records,previous):
                    if old and any(old.get(k)!=v for k,v in value.items() if k!='bigquery'):raise ValueError('Historical fixture is immutable')
                for (ref,value),old in zip(records,previous):
                    if not old:tx.create(ref,value)
            write(store.client.transaction(max_attempts=5))
            if store.pending_fact(key) is not None:
                self.analytics.insert_outcome(response,ep)
                @firestore.transactional
                def acknowledged(tx):
                    self._scope(tx,generation)
                    store.acknowledge_fact(key,response,transaction=tx)
                acknowledged(store.client.transaction(max_attempts=5))
        for step in (batch[:5],batch[5:]):
            state=store.calibration_state(batch[0].episode.area,is_demo=True,generation=generation) or CalibrationState(area=batch[0].episode.area,is_demo=True,scenario_generation=generation)
            store.calibrate(state,step,now=anchor)
        final=store.calibration_state(batch[0].episode.area,is_demo=True,generation=generation)
        if final is None:raise ValueError('Fixture calibration unavailable')
        return {'generation':generation,'historical_shop_episodes':6,'synthetic_shops':1,'multiplier':final.multiplier,'version':final.version,'note':'Six labelled historical episodes of one synthetic shop; not independent shops, Telegram acceptance or accuracy.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    settings=load_settings();require_local(settings,os.environ)
    if not args.apply:print('Local guards passed. Use --apply to add immutable synthetic history after the six owned fixture shops exist.');return
    from api.tools.firestore import create_firestore_client
    from api.tools.cloud_events import create_analytics_client
    client=create_firestore_client(settings);analytics=None
    try:
        store=FirestoreOutcomeStore(client,settings.hash_salt)
        analytics=OutcomeAnalytics(create_analytics_client(settings),settings.gcp_project,settings.bigquery_dataset,store,emulator_host=os.environ['BIGQUERY_EMULATOR_HOST'])
        print(OutcomeFixtureSeeder(store,analytics).seed(now=datetime.now(UTC)))
    finally:
        try:
            if analytics:analytics.close()
        finally:client.close()
if __name__=='__main__':main()
