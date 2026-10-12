"""Repeatable synthetic fixtures through existing private originals/evidence sinks.

Run only against explicitly validated loopback emulators. This does not run an
inventory model or invent Telegram recipients, delivery or self-reported actions.
"""
import argparse
import json
from datetime import UTC,datetime
from hashlib import sha256
import os
from pathlib import Path
from typing import Iterator
from api.tools.storage import OriginalStorage
from api.media import EvidenceLedger
from api.dispatch_models import Shop,Recipient
from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore
from api.demo_transport import require_local_demo
from api.demo_scenario import ScenarioResetBusy,FIXTURE_ORIGIN,SHOP_IDS
from api.inventory_models import InventoryAssessment
from api.lift_first import rank_lift_first
from api.media_models import MediaRecord,MAX_UPLOAD_BYTES



def fixture_shops() -> Iterator[dict]:
    kinds=('grocery','hardware','electronics','grocery','other','electronics')
    vehicles=('car','van','motorcycle',None,None,None)
    for i,identity in enumerate(SHOP_IDS):
        assessment=InventoryAssessment(items=[dict(name='Synthetic rice cartons',category='food',qty=4.,est_unit_value_rm=40.+i*10.,location_in_shop='Illustrative left floor stock',height='floor',lift_effort=2,timestamp_s=0.),dict(name='Synthetic water cases',category='food',qty=6.,est_unit_value_rm=12.+i*2.,location_in_shop='Illustrative centre floor stock',height='floor',lift_effort=1,timestamp_s=0.),dict(name='Synthetic rice cookers',category='appliances',qty=3.,est_unit_value_rm=80.+i*20.,location_in_shop='Illustrative low right shelf',height='low',lift_effort=1,timestamp_s=0.)],confidence=.3,confidence_note='Manually defined synthetic fixture estimates; not a model result or real-shop valuation.')
        yield dict(shop_id=identity,shop_name=f'Synthetic Demo Shop {i+1}',shop_type=kinds[i],lat=3.0315+i*.0005,lng=101.5356+i*.0004,is_demo=True,fixture_origin=FIXTURE_ORIGIN,recipients=[],virtual_recipient=dict(key=f'fixture-shop-{i+1}',language=('en','ms','zh','ta','bn','id')[i]),has_vehicle=vehicles[i] is not None,vehicle_type=vehicles[i],floor='ground' if i<4 else 'upper',river_or_past_event_exposure=i%2==0,risk_score=40*(i<4)+20*(vehicles[i] is not None)+20*(i%2==0),risk_score_missing=[],risk_score_provisional=False,assessment=assessment)


class FixtureSeeder:
    def __init__(self,client:firestore.Client,storage:OriginalStorage,ledger:EvidenceLedger,*,prefix:str='') -> None:
        self.client,self.storage,self.ledger,self.prefix=client,storage,ledger,prefix

    def seed(self,data:bytes) -> dict:
        if not 12<=len(data)<=MAX_UPLOAD_BYTES or data[4:8]!=b'ftyp':raise ValueError('A bounded original MP4 fixture is required')
        digest=sha256(data).hexdigest()
        scenario_ref=self.client.collection(self.prefix+'demo_scenario').document('current')
        for fixture in fixture_shops():
            identity=fixture['shop_id'];assessment=fixture.pop('assessment')
            Shop.model_validate(fixture)
            shop_ref=self.client.collection(self.prefix+'shops').document(identity)
            media_id=sha256(f'{FIXTURE_ORIGIN}:{identity}:{digest}'.encode()).hexdigest()
            media_ref=self.client.collection(self.prefix+'media').document(media_id)
            inventory_id=sha256(f'{FIXTURE_ORIGIN}:{identity}:inventory:{digest}'.encode()).hexdigest()
            inventory_ref=self.client.collection(self.prefix+'inventories').document(inventory_id)
            now=datetime.now(UTC)
            record=MediaRecord(media_id=media_id,shop_id=identity,kind='baseline_video',sender_hash=sha256((FIXTURE_ORIGIN+identity).encode()).hexdigest(),sha256=digest,bytes=len(data),mime_type='video/mp4',gcs_uri=self.storage.uri(media_id),uploaded_at=now,telegram_date=None,received_at=now,origin='local_fixture',lat=fixture['lat'],lng=fixture['lng'],location_attribution='unconfirmed_shop',is_demo=True)
            @firestore.transactional
            def reserve(tx):
                scenario=scenario_ref.get(transaction=tx,timeout=8,retry=None).to_dict() or {}
                old=shop_ref.get(transaction=tx,timeout=8,retry=None).to_dict();old_media=media_ref.get(transaction=tx,timeout=8,retry=None).to_dict()
                if scenario.get('state')=='resetting':raise ScenarioResetBusy('Demo reset in progress')
                if old and (old.get('fixture_origin')!=FIXTURE_ORIGIN or old.get('is_demo') is not True):raise ValueError('Fixture identity is owned by another registration')
                if not old_media:tx.create(media_ref,record.model_dump())
                return MediaRecord.model_validate(old_media) if old_media else record
            record=reserve(self.client.transaction())
            self.storage.create_original(media_id,data,'video/mp4',digest)
            # Streaming append uses a stable insertion identity. Physical duplicate
            # rows remain append-only and readers dedupe media_id, as with uploads.
            if record.ledger_status!='done':self.ledger.append(record)
            lift=[row.model_dump() for row in rank_lift_first(assessment)]
            inventory=dict(inventory_id=inventory_id,shop_id=identity,kind='baseline',media_id=media_id,created_at=record.received_at,items=[row.model_dump() for row in assessment.items],total_est_value_rm=round(sum(row.qty*row.est_unit_value_rm for row in assessment.items),2),lift_first=lift,lift_first_value_rm=round(sum(row['value_rm'] for row in lift),2),confidence=assessment.confidence,confidence_note=assessment.confidence_note,is_demo=True,provenance='synthetic_fixture')
            @firestore.transactional
            def finish(tx):
                scenario=scenario_ref.get(transaction=tx,timeout=8,retry=None).to_dict() or {}
                old=shop_ref.get(transaction=tx,timeout=8,retry=None).to_dict();existing=inventory_ref.get(transaction=tx,timeout=8,retry=None)
                if scenario.get('state')=='resetting':raise ScenarioResetBusy('Demo reset in progress')
                if old and (old.get('fixture_origin')!=FIXTURE_ORIGIN or old.get('is_demo') is not True):raise ValueError('Fixture identity is owned by another registration')
                tx.update(media_ref,{'storage_status':'done','ledger_status':'done','status':'complete'})
                if not existing.exists:tx.create(inventory_ref,inventory)
                if not old:tx.create(shop_ref,{**fixture,'baseline_inventory_id':inventory_id,'inventory_at':record.received_at,'lift_first':lift,'lift_first_value_rm':inventory['lift_first_value_rm'],'active_danger':False})
                if not scenario:tx.set(scenario_ref,{'generation':1,'state':'ready','started_at':now,'fixture_shop_ids':list(SHOP_IDS)})
                elif 'fixture_shop_ids' not in scenario:tx.update(scenario_ref,{'fixture_shop_ids':list(SHOP_IDS)})
            finish(self.client.transaction())
        from api.destinations import SafePoint
        for raw in json.loads((Path(__file__).resolve().parents[1]/'infra/data/safe_points.json').read_text()):
            SafePoint.model_validate(raw)
            try:self.client.collection(self.prefix+'safe_points').document(raw['safe_point_id']).create(raw,timeout=8,retry=None)
            except AlreadyExists:pass
        return dict(synthetic_shops=6,vehicles=3,transport='local_virtual',inventory_provenance='synthetic_fixture')

    def bind_registered(self,fixture_id:int,registration_id:str) -> None:
        """Explicit operator action. Copy a real registered owner only, never guessed IDs."""
        if not 1<=fixture_id<=6:raise ValueError('Fixture must be 1 through 6')
        ref=self.client.collection(self.prefix+'shops').document(SHOP_IDS[fixture_id-1])
        source=self.client.collection(self.prefix+'shops').document(registration_id)
        scenario_ref=self.client.collection(self.prefix+'demo_scenario').document('current')
        @firestore.transactional
        def bind(tx):
            scenario=scenario_ref.get(transaction=tx,timeout=8,retry=None).to_dict() or {}
            fixture=ref.get(transaction=tx,timeout=8,retry=None).to_dict() or {};registered=source.get(transaction=tx,timeout=8,retry=None).to_dict() or {}
            if scenario.get('state')=='resetting':raise ScenarioResetBusy('Demo reset in progress')
            owners=[Recipient.model_validate(r).model_dump() for r in registered.get('recipients',[]) if r.get('role')=='owner']
            if fixture.get('fixture_origin')!=FIXTURE_ORIGIN or not fixture.get('is_demo') or registered.get('is_demo') or len(owners)!=1:raise ValueError('An ordinary registered owner and owned fixture are required')
            tx.update(ref,{'recipients':owners,'virtual_recipient':None,'binding_provenance':'explicit_operator_registered_owner'})
        bind(self.client.transaction())


def main() -> None:
    from api.config import load_settings
    from api.tools.firestore import create_firestore_client
    from api.tools.storage import create_storage_client,OriginalStorage
    from api.tools.cloud_events import create_analytics_client
    from api.media import EvidenceLedger
    from api.tools.emulators import loopback_endpoint
    parser=argparse.ArgumentParser(description='Seed synthetic fixtures in local emulators only')
    parser.add_argument('--bind-fixture',type=int);parser.add_argument('--registered-shop')
    parser.add_argument('--consenting-owner',action='store_true')
    args=parser.parse_args();settings=load_settings();require_local_demo(settings)
    loopback_endpoint(os.environ.get('STORAGE_EMULATOR_HOST',''),http=True)
    if not settings.demo_virtual_delivery:raise ValueError('DEMO_VIRTUAL_DELIVERY=true is required')
    if args.bind_fixture is None and (args.registered_shop or args.consenting_owner):raise ValueError('Binding flags require --bind-fixture')
    if args.bind_fixture is not None and (not args.registered_shop or not args.consenting_owner):raise ValueError('Explicit existing registration and consenting-owner acknowledgement required')
    client=create_firestore_client(settings);storage=OriginalStorage(create_storage_client(settings),settings.gcs_bucket);analytics=create_analytics_client(settings)
    try:
        seed=FixtureSeeder(client,storage,EvidenceLedger(analytics,settings.gcp_project,settings.bigquery_dataset))
        result=seed.seed((Path(__file__).resolve().parents[1]/'demo/media/synthetic-before-still.mp4').read_bytes())
        if args.bind_fixture is not None:seed.bind_registered(args.bind_fixture,args.registered_shop)
        print(result)
    finally:client.close();storage.close();analytics.close()

if __name__=='__main__':main()
