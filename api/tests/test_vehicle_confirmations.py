"""Real local Firestore transactions and public private-recipient callbacks."""
import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from api.agents.sessions import session_user_id
from api.alert_composer import AlertComposer, snapshot_actions
from api.config import Settings
from api.destinations import DestinationLookup, SafePoint
from api.dispatch_models import Shop, ActionSnapshot
from api.main import create_app
from api.telegram_inbox import FirestoreInbox
from api.telegram_webhook import TelegramHandler
from api.tools.firestore import create_firestore_client
from api.vehicle_confirmations import VehicleActionStore, VehicleConfirmationService


class Bot:
    def __init__(self): self.answers=[]
    def answer_callback_query(self, identity, text): self.answers.append((identity,text))


class Sink:
    def __init__(self): self.rows=[];self.fail=True
    def insert_confirmation(self,row):
        if self.fail:raise OSError('simulated sink outage')
        self.rows.append(row)


@pytest.fixture
def domain():
    if not os.environ.get('FIRESTORE_EMULATOR_HOST'):pytest.skip('Firestore emulator required')
    client=create_firestore_client(Settings(gcp_project='highground-task8-tests'))
    prefix='vehicle-test-'+uuid4().hex
    store=VehicleActionStore(client,actions=prefix+'a',current=prefix+'c',confirmations=prefix+'f',alerts=prefix+'l',shops=prefix+'s')
    inbox=FirestoreInbox(client,prefix+'i')
    shop=Shop(shop_id='synthetic',shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,has_vehicle=True,vehicle_type='car',
              recipients=[{'telegram_chat_id':101,'language':'en','role':'owner'},{'telegram_chat_id':102,'language':'en','role':'worker'}])
    client.collection(store.shops).document(shop.shop_id).set(shop.model_dump())
    event={'event_id':'warning-one','episode_id':'episode-one','level':'warning','is_demo':True,'created_at':datetime.now(UTC)}
    record=store.prepare(event,shop,snapshot_actions(event,shop),'salt')
    for recipient in shop.recipients:
        identity=session_user_id(recipient.telegram_chat_id,'salt')
        alert_id=sha256(f"{event['event_id']}:{shop.shop_id}:{identity}".encode()).hexdigest()
        client.collection(store.alerts).document(alert_id).set({'status':'accepted','message_id':recipient.telegram_chat_id+1000,'level':'warning','snapshot':record['snapshot']})
    try:yield client,store,inbox,shop,event,record
    finally:
        for collection in (store.actions,store.current,store.confirmations,store.alerts,store.shops,inbox.collection,prefix+'points'):
            for doc in client.collection(collection).stream():doc.reference.delete()
        client.close()


def test_public_concurrent_recipients_replay_and_recoverable_outbox(domain):
    client,store,inbox,shop,event,record=domain
    sink=Sink();bot=Bot();service=VehicleConfirmationService(store,sink,hash_salt='salt')
    handler=TelegramHandler(inbox,bot,confirmations=service)
    app=create_app(Settings(telegram_webhook_secret='synthetic'),handler)
    def payload(sender,identity,update=1,msg=None):return {'update_id':update,'callback_query':{'id':identity,'from':{'id':sender},'data':'vehicle:'+record['action_id'],
        'message':{'message_id':msg or sender+1000,'chat':{'id':sender,'type':'private'}}}}
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'}) as http:
            responses=await asyncio.gather(http.post('/telegram/webhook',json=payload(101,'owner')),http.post('/telegram/webhook',json=payload(102,'worker',2)))
            assert all(response.status_code==200 for response in responses)
            assert (await http.post('/telegram/webhook',json=payload(101,'owner'))).status_code==200
            assert len(bot.answers)==2
            assert (await http.post('/telegram/webhook',json=payload(999,'forged',3))).status_code==200
            assert (await http.post('/telegram/webhook',json=payload(101,'wrong-message',4,msg=9))).status_code==200
        rows=list(client.collection(store.confirmations).stream())
        assert len(rows)==1
        row=rows[0].to_dict()
        assert row['self_reported'] is True and row['protected_value_rm'] is None and row['episode_id']=='episode-one'
        assert row['snapshot']==record['snapshot'] and row['bigquery']=='pending'
        sink.fail=False
        await VehicleConfirmationService(store,sink,hash_salt='salt').resume_pending()
        await service.resume_pending()
        assert len(sink.rows)==1 and sink.rows[0]['confirmation_id']==record['action_id']
        assert rows[0].reference.get().to_dict()['bigquery']=='done'
    asyncio.run(run())


def test_binding_revocation_supersede_and_danger_guard(domain):
    client,store,inbox,shop,event,record=domain
    def confirm():return store.record(record['action_id'],sender_chat_id=101,message_chat_id=101,message_id=1101,sender_hash=session_user_id(101,'salt'),now=datetime.now(UTC))[0]
    ref=client.collection(store.shops).document(shop.shop_id)
    ref.update({'recipients':[shop.recipients[1].model_dump()]})
    assert confirm()=='unavailable'
    ref.update({'recipients':[r.model_dump() for r in shop.recipients]})
    alert=next(client.collection(store.alerts).stream())
    # Immutable action survives mutable registration changes.
    ref.update({'vehicle_type':'van'})
    assert confirm()=='recorded'
    newer={**event,'event_id':'warning-two','created_at':event['created_at']+timedelta(seconds=1)}
    store.prepare(newer,shop,snapshot_actions(newer,shop),'salt')
    assert confirm()=='superseded'
    store.supersede(shop.shop_id,event_id='danger',episode_id='episode-one',at=newer['created_at']+timedelta(seconds=1))
    assert ref.get().to_dict()['active_danger'] is True
    latest={**event,'event_id':'warning-three','created_at':newer['created_at']+timedelta(seconds=2)}
    assert store.prepare(latest,shop,snapshot_actions(latest,shop),'salt')['state']=='superseded'


def test_registry_real_only_provenance_cutoff_and_fixed_danger(domain):
    client,store,inbox,shop,event,record=domain
    collection=inbox.collection[:-1]+'points'
    records=json.loads(Path('infra/data/safe_points.json').read_text())
    for raw in records:client.collection(collection).document(raw['safe_point_id']).set(raw)
    fake={**records[1],'safe_point_id':'fictional','name':'Fictional','lat':3.,'lng':101.,'is_demo':True}
    client.collection(collection).document('fictional').set(fake)
    lookup=DestinationLookup(client,collection=collection,radius_m=20000)
    assert lookup.nearest(3.,101.,('pps',)) is None
    destination=lookup.nearest(records[1]['lat'],records[1]['lng'],('pps',))
    assert destination.name==records[1]['name'] and destination.opening_status=='unknown'
    assert destination.min_level is None and destination.coordinate_provenance
    async def run():
        composer=AlertComposer(destinations=lookup)
        located=shop.model_copy(update={'lat':records[1]['lat'],'lng':records[1]['lng']})
        from api.i18n import danger_text
        body,snapshot,markup=await composer.compose({**event,'level':'danger'},located,'en')
        assert body==danger_text('en',is_demo=True,safe_point_name=destination.name,route_link=destination.route_link)
        assert markup['inline_keyboard']==[[{'text':'View route','url':destination.route_link}]]
        assert snapshot.vehicle_type is None and snapshot.items==()
    asyncio.run(run())
    invalid={**records[0],'min_level':2,'min_level_source':None}
    with pytest.raises(ValueError):SafePoint.model_validate(invalid)


def test_public_simulation_rejects_internal_controls():
    from api.tests.test_dispatch import service
    from api.dispatch_router import create_dispatch_router
    from fastapi import FastAPI
    active,*_=service()
    app=FastAPI();app.include_router(create_dispatch_router(Settings(demo_mode=True,operator_token='synthetic'),active))
    body={'request_id':'boundary','level':'danger','lat':3.,'lng':101.}
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test',headers={'Authorization':'Bearer synthetic'}) as http:
            for key,value in {'is_demo':False,'simulation':False,'processing_started_at':'2000-01-01T00:00:00Z','episode_id':'forged','warning_structure':'warning_intro_fallback','reporter_shop_id':'hidden'}.items():
                assert (await http.post('/demo/simulate-warning',json={**body,key:value})).status_code==400
            first=await http.post('/demo/simulate-warning',json=body)
            again=await http.post('/demo/simulate-warning',json=body)
            assert first.status_code==again.status_code==200 and first.json()['event_id']==again.json()['event_id']
    asyncio.run(run())


def test_first_receipt_is_metadata_not_retry_fingerprint(domain):
    from api.dispatch_store import FirestoreDispatchStore
    from api.dispatch_models import EventRequest
    client,_,inbox,*_=domain
    store=FirestoreDispatchStore(client,events=inbox.collection+'events')
    first=datetime.now(UTC)-timedelta(seconds=20)
    request=EventRequest(request_id='receipt',level='warning',lat=3.,lng=101.,processing_started_at=first)
    try:
        one=store.ensure_event(request,datetime.now(UTC))
        two=store.ensure_event(request.model_copy(update={'processing_started_at':datetime.now(UTC)}),datetime.now(UTC))
        assert one['event_id']==two['event_id'] and two['processing_started_at']==first
    finally:
        for document in client.collection(store.events).stream():document.reference.delete()


def test_lazy_media_configuration_does_not_construct_upload_clients(monkeypatch):
    import api.photo_reports as reports
    def forbidden(*args,**kwargs):raise AssertionError('constructed media clients without an upload')
    monkeypatch.setattr(reports,'create_photo_report_service',forbidden)
    service=reports.LazyPhotoReportService(Settings())
    assert service.active is None
    asyncio.run(service.close())


def test_callback_feedback_fits_official_limit():
    from api.i18n import catalog,text
    for language in ('en','ms','zh','ta','bn','ne','my','id'):
        for key in ('vehicle_recorded','vehicle_already_recorded','confirmation_superseded','confirmation_unavailable'):
            feedback=text(language,key)
            if not catalog(language)['_reviewed']:feedback+='\n'+text(language,'translation_notice')
            assert len(feedback)<=200


def test_public_photo_chooses_validated_largest_and_ack_precedes_work(domain):
    from api.photo_models import PhotoReply
    client,store,inbox,*_=domain
    effects=[]
    class Photos:
        async def handle_photo(self,chat,update,message,date,photo,processing_started_at=None):
            effects.append(('photo',photo.file_id,date,processing_started_at))
            return PhotoReply(code='confirm_at_shop',text='Confirm location')
        async def recheck_reply(self,chat,reply):return reply
        async def pending_location_report_id(self,chat):return 'a'*32
        async def confirm_report_location(self,chat,identity,**kwargs):
            effects.append(('confirm',identity,kwargs))
            return PhotoReply(code='share_location',text='Share location')
    class Sender:
        def answer_callback_query(self,identity,text):effects.append(('ack',identity))
        def send_message(self,chat,text,reply_markup=None):effects.append(('send',text));return 50
    handler=TelegramHandler(inbox,Sender(),photos=Photos())
    app=create_app(Settings(telegram_webhook_secret='synthetic'),handler)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'}) as http:
            photo={'update_id':90,'message':{'message_id':91,'date':100,'chat':{'id':101,'type':'private'},'photo':[
                {'file_id':'largest','file_unique_id':'one','width':100,'height':100,'file_size':1000},
                {'file_id':'small','file_unique_id':'two','width':10,'height':10,'file_size':50}]}}
            assert (await http.post('/telegram/webhook',json=photo)).status_code==200
            assert effects[0][0:3]==('photo','largest',100) and effects[0][3].tzinfo is not None
            callback={'update_id':92,'callback_query':{'id':'photo-callback','from':{'id':101},'data':'photo:'+('a'*32)+':no','message':{'message_id':50,'chat':{'id':101,'type':'private'}}}}
            assert (await http.post('/telegram/webhook',json=callback)).status_code==200
            assert [effect[0] for effect in effects[-3:]]==['ack','confirm','send']
            assert (await http.post('/telegram/webhook',json=callback)).status_code==200
            assert len(effects)==5
            malformed={**photo,'update_id':93,'message':{**photo['message'],'photo':[{'file_id':'x','file_unique_id':'x','width':True,'height':1}]}}
            assert (await http.post('/telegram/webhook',json=malformed)).status_code==400
            missing_date={**photo,'update_id':94,'message':{key:value for key,value in photo['message'].items() if key!='date'}}
            assert (await http.post('/telegram/webhook',json=missing_date)).status_code==400
    asyncio.run(run())


def test_lookup_tie_type_and_closed_records(domain):
    client,store,inbox,*_=domain
    collection=inbox.collection[:-1]+'points'
    template=json.loads(Path('infra/data/safe_points.json').read_text())[0]
    for identity,name,kind,opening in [('z','Z','parking','unknown'),('a','A','parking','unknown'),('0','Closed','parking','closed'),('pps','Shelter','pps','unknown')]:
        row={**template,'safe_point_id':identity,'name':name,'type':kind,'lat':3.,'lng':101.,'opening_status':opening}
        client.collection(collection).document(identity).set(row)
    client.collection(collection).document('malformed').set({'lat':3.,'lng':101.})
    lookup=DestinationLookup(client,collection=collection,radius_m=1)
    assert lookup.nearest(3.,101.,('parking',)).name=='A'
    assert lookup.nearest(3.,101.,('pps',)).name=='Shelter'
    assert lookup.nearest(3.0001,101.,('parking',)) is None
    with pytest.raises(ValueError):lookup.nearest(float('nan'),101.,('pps',))


def test_warning_separate_routes_and_bound_action_button(domain):
    client,store,inbox,shop,event,record=domain
    collection=inbox.collection[:-1]+'points'
    records=json.loads(Path('infra/data/safe_points.json').read_text())
    for raw in records:client.collection(collection).document(raw['safe_point_id']).set(raw)
    located=shop.model_copy(update={'lat':records[0]['lat'],'lng':records[0]['lng']})
    async def run():
        composer=AlertComposer(destinations=DestinationLookup(client,collection=collection,radius_m=20000))
        snapshot=await composer.action_snapshot(event,located)
        action=store.prepare({**event,'event_id':'destinations'},located,snapshot,'salt')
        frozen=ActionSnapshot.model_validate(action['snapshot'])
        body,actual,markup=await composer.compose({**event,'event_id':'destinations','lat':located.lat,'lng':located.lng},located,'en',snapshot_override=frozen)
        assert actual==frozen
        controls=[button for row in markup['inline_keyboard'] for button in row]
        assert len(controls)==3 and controls[0]['callback_data']=='vehicle:'+action['action_id']
        assert controls[1]['url']==frozen.parking_destination.route_link
        assert controls[2]['url']==frozen.shelter_destination.route_link
        assert '2022' in body and 'Current opening and route conditions are unconfirmed.' in body and 'Minimum parking level is unconfirmed' in body
        assert all('stock:' not in str(button) for button in controls)
    asyncio.run(run())


def test_real_firestore_keyboard_dispatch_and_same_id_preparation_retry(domain):
    from google.api_core.exceptions import InvalidArgument
    from api.dispatch import DispatchService
    from api.dispatch_store import FirestoreDispatchStore
    from api.dispatch_models import EventRequest
    from api.tests.test_dispatch import Sinks
    client,actions,inbox,shop,*_=domain
    collection=inbox.collection[:-1]+'points'
    records=json.loads(Path('infra/data/safe_points.json').read_text())
    for raw in records:client.collection(collection).document(raw['safe_point_id']).set(raw)
    located=shop.model_copy(update={'lat':records[0]['lat'],'lng':records[0]['lng']})
    client.collection(actions.shops).document(shop.shop_id).set(located.model_dump())
    store=FirestoreDispatchStore(client,events=inbox.collection+'events',alerts=actions.alerts,shops=actions.shops)
    class Sender:
        def __init__(self):self.sent=[]
        def send_message(self,chat,text,reply_markup=None):self.sent.append((chat,text,reply_markup));return 1000+chat
    class OldStore(FirestoreDispatchStore):
        def prepare_alert(self,alert):
            # Reproduce the live failure with the actual SDK and emulator.
            self.client.collection(self.alerts).document(alert['alert_id']).create({key:value for key,value in alert.items() if key!='telegram_chat_id'})
    sender=Sender()
    composer=AlertComposer(destinations=DestinationLookup(client,collection=collection,radius_m=20000))
    request=EventRequest(request_id='keyboard-retry',level='warning',lat=located.lat,lng=located.lng)
    old=OldStore(client,events=store.events,alerts=store.alerts,shops=store.shops)
    async def run():
        broken=DispatchService(old,sender,Sinks(),hash_salt='salt',composer=composer,vehicle_actions=actions)
        with pytest.raises(InvalidArgument):await broken.process(request)
        event_id=sha256(b'demo:keyboard-retry').hexdigest()
        assert store.get_event(event_id)['prepared'] is False and not sender.sent
        fixed=DispatchService(store,sender,Sinks(),hash_salt='salt',composer=composer,vehicle_actions=actions)
        result=await fixed.process(request)
        assert result['event_id']==event_id and result['status']=='complete' and len(sender.sent)==2
        for identity in store.get_event(event_id)['alert_ids']:
            stored=client.collection(store.alerts).document(identity).get().to_dict()
            assert isinstance(stored['reply_markup'],str)
            recovered=store.get_alert(identity)['reply_markup']
            assert recovered==json.loads(stored['reply_markup'])
            controls=[button for row in recovered['inline_keyboard'] for button in row]
            assert len(controls)==3 and controls[0]['callback_data'].startswith('vehicle:')
            assert controls[1]['url']==records_to_route(records[0]) and controls[2]['url']==records_to_route(records[1])
            assert recovered in [wire[2] for wire in sender.sent]
        await fixed.process(request)
        assert len(sender.sent)==2
        danger=await fixed.process(request.model_copy(update={'request_id':'keyboard-danger','level':'danger'}))
        assert danger['status']=='complete' and len(sender.sent)==4
        for identity in store.get_event(danger['event_id'])['alert_ids']:
            recovered=store.get_alert(identity)['reply_markup']
            assert recovered['inline_keyboard']==[[{'text':'View route','url':records_to_route(records[1])}]]
            assert recovered in [wire[2] for wire in sender.sent[-2:]]
    try:asyncio.run(run())
    finally:
        for collection in (store.events,store.plans,store.deliveries):
            for document in client.collection(collection).stream():document.reference.delete()


def records_to_route(record):
    return f"https://www.google.com/maps/dir/?api=1&destination={record['lat']},{record['lng']}"


def test_firestore_markup_none_and_legacy_object_read(domain):
    from api.dispatch_store import FirestoreDispatchStore
    client,actions,inbox,*_=domain
    store=FirestoreDispatchStore(client,alerts=actions.alerts)
    for identity,markup in [('none',None),('legacy',{'remove_keyboard':True})]:
        client.collection(store.alerts).document(identity).set({'alert_id':identity,'reply_markup':markup})
        delivery=client.collection(store.deliveries).document(identity)
        delivery.set({'telegram_chat_id':101})
        try:assert store.get_alert(identity)['reply_markup']==markup
        finally:delivery.delete()


@pytest.mark.parametrize('failure_stage',['claim_sink','finish_sink'])
def test_public_callback_survives_optional_outbox_transaction_abort(domain,monkeypatch,failure_stage):
    """A durable confirmation and acknowledgement survive optional sink outages."""
    from google.api_core.exceptions import Aborted
    client,store,inbox,shop,event,record=domain
    sink=Sink();bot=Bot();service=VehicleConfirmationService(store,sink,hash_salt='salt')
    handler=TelegramHandler(inbox,bot,confirmations=service)
    app=create_app(Settings(telegram_webhook_secret='synthetic'),handler)
    original=getattr(store,failure_stage);calls=0
    def abort_once(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==1:
            raise ValueError('Failed to commit transaction in 5 attempts.') from Aborted('Transaction lock timeout.')
        return original(*args,**kwargs)
    monkeypatch.setattr(store,failure_stage,abort_once)
    callback_id='outbox-'+failure_stage
    payload={'update_id':91,'callback_query':{'id':callback_id,'from':{'id':101},'data':'vehicle:'+record['action_id'],
             'message':{'message_id':1101,'chat':{'id':101,'type':'private'}}}}
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'}) as http:
            response=await http.post('/telegram/webhook',json=payload)
            facts=list(client.collection(store.confirmations).stream())
            assert len(facts)==1 and len(bot.answers)==1
            assert facts[0].to_dict()['bigquery']=='pending'
            assert response.status_code==200
            operation=sha256(('callback:'+callback_id).encode()).hexdigest()
            assert client.collection(inbox.collection).document(operation).get().to_dict()['status']=='done'
            assert (await http.post('/telegram/webhook',json=payload)).status_code==200
            assert len(bot.answers)==1 and len(list(client.collection(store.confirmations).stream()))==1
        fact=facts[0].to_dict()
        if failure_stage=='finish_sink':
            # Failed completion preserves the lease. Once that lease expires,
            # restart can resume the pending immutable logical confirmation.
            assert fact['sink_lease_until']>datetime.now(UTC)
            facts[0].reference.update({'sink_lease_until':datetime.now(UTC)-timedelta(seconds=1)})
        else:
            assert 'sink_owner' not in fact
        sink.fail=False
        await VehicleConfirmationService(store,sink,hash_salt='salt').resume_pending()
        await service.resume_pending()
        assert len(sink.rows)==1 and sink.rows[0]['confirmation_id']==record['action_id']
        assert facts[0].reference.get().to_dict()['bigquery']=='done'
    asyncio.run(run())
