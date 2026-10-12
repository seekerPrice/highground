import asyncio
from datetime import UTC,datetime,timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from api.photo_models import PhotoAssessment,PhotoMedia
from api.photo_reports import triage_photo,PhotoReportService
from api.photo_store import PhotoStore
from api.media_models import MediaIngestError
from api.config import Settings
from api.tools.firestore import create_firestore_client
from api.tests.test_media import service as media_service,image_bytes


def assessment(**updates):
    data=dict(scene='flooding',assessment_status='assessed',is_flooding=True,water_location='street',
              est_depth_cm=None,confidence=.7,reason='Water depicted on a street.')
    data.update(updates);return PhotoAssessment(**data)

def test_deterministic_confidence_inside_and_independent_reports():
    assert triage_photo(assessment(),[])[0]=='warning'
    assert triage_photo(assessment(water_location='inside_premises'),[])[0]=='danger'
    assert triage_photo(assessment(confidence=.699),[])[0]=='watch'
    reports=[dict(shop_id='a',sha256='one',confidence=.4,corroboration_eligible=True),
             dict(shop_id='b',sha256='two',confidence=.5,corroboration_eligible=True)]
    assert triage_photo(assessment(confidence=.4),reports)[0]=='warning'
    reports[1]['shop_id']='a';assert triage_photo(assessment(confidence=.4),reports)[0]=='watch'
    reports[1]['shop_id']='b';reports[1]['sha256']='one';assert triage_photo(assessment(confidence=.4),reports)[0]=='watch'
    reports[1]['sha256']='two';reports[1]['corroboration_eligible']=False
    assert triage_photo(None,reports)[0]=='watch'

@pytest.mark.parametrize('changes',[
    {'confidence':float('nan')},{'scene':'screenshot','is_flooding':True},
    {'is_flooding':False,'water_location':'inside_premises'}, {'est_depth_cm':-1},
    {'reason':'word '*21},{'assessment_status':'uncertain','confidence':.9}])
def test_assessment_rejects_inconsistent_or_nonfinite_output(changes):
    with pytest.raises(ValidationError):assessment(**changes)

class Assessor:
    def __init__(self,value):self.value=value;self.calls=0
    async def assess(self,*args):self.calls+=1;return self.value
    async def close(self):pass
class Dispatch:
    def __init__(self):self.events=[];self.composer=SimpleNamespace(destinations=None);self.vehicle_actions=None
    async def process(self,event):self.events.append(event);return {'event_id':'stable-event','status':'complete'}

@pytest.mark.skipif(not __import__('os').environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_real_photo_store_immediate_receipt_confirmation_window_retry_and_fencing():
    client=create_firestore_client(Settings(gcp_project='highground-task9-tests'))
    prefix='photo-test-'+uuid4().hex+'-';store=PhotoStore(client,'synthetic',prefix)
    shop_ref=store.collection('shops').document('reporter')
    shop_ref.set(dict(shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,
                      recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    media,media_store,download,storage,ledger=media_service()
    media.authorize=store.authorize_media
    assessor=Assessor(assessment(confidence=.4));dispatch=Dispatch()
    now=datetime.now(UTC);active=PhotoReportService(store,media,assessor,dispatch,clock=lambda:now)
    photo=PhotoMedia(file_id='opaque-file',file_unique_id='opaque-unique',file_size=len(image_bytes()))
    async def run():
        reply=await active.handle_photo(123,1,1,int(now.timestamp()),photo)
        assert reply.code=='confirm_at_shop' and ledger.ids and not dispatch.events
        assert media_store.record.location_attribution=='unconfirmed_shop'
        assert all(len(button['callback_data'].encode())<=64 for row in reply.reply_markup['inline_keyboard'] for button in row)
        assert store.recent_reports(3.,101.,now,True)==[]
        duplicate=await active.handle_photo(123,1,1,int(now.timestamp()),photo)
        assert duplicate.report_id==reply.report_id and download.calls==1
        second=await active.handle_photo(123,2,2,int(now.timestamp()),PhotoMedia(file_id='other',file_unique_id='other',file_size=10))
        assert second.code=='rate_limited'
        shared=await active.confirm_report_location(123,reply.report_id,at_shop=False)
        assert shared.code=='share_location'
        shared=await active.confirm_report_location(123,reply.report_id,lat=3.001,lng=101.001)
        assert shared.code=='confirm_shared_location' and not dispatch.events
        done=await active.confirm_report_location(123,reply.report_id,at_shop=True)
        assert done.code=='report_recorded' and len(dispatch.events)==1
        report=store.get(reply.report_id)
        assert (report['lat'],report['lng'],report['location_attribution'])==(3.001,101.001,'confirmed_shared')
        assert (media_store.record.lat,media_store.record.lng,media_store.record.location_attribution)==(3.,101.,'unconfirmed_shop')
        assert dispatch.events[0].reporter_shop_id=='reporter' and dispatch.events[0].simulation
        assert dispatch.events[0].warning_structure=='warning_intro_fallback'
        window=store.recent_reports(3.001,101.001,now,True)
        assert len(window)==1 and window[0]['shop_id']=='reporter'
        owner=store.claim(reply.report_id);store.release(reply.report_id,owner)
        later=store.claim(reply.report_id)
        with pytest.raises(MediaIngestError):store.update(reply.report_id,owner,status='wrong')
        store.release(reply.report_id,later)
    try:asyncio.run(run())
    finally:
        for name in ('shops','photo_reports','photo_pending','photo_rate'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()

@pytest.mark.parametrize('current,other_shop,other_hash,other_status,expected',[
    (None,'other','different','unverified','warning'),
    (assessment(scene='unreadable',assessment_status='uncertain',is_flooding=False,water_location='none',confidence=.2),'other','different','positive','warning'),
    (None,'other','different','rejected','watch'),
    (None,'reporter','different','unverified','watch'),
    (None,'other','same','unverified','watch'),
    (assessment(scene='screenshot',is_flooding=False,water_location='none',confidence=.9),'other','different','positive',None),
])
@pytest.mark.skipif(not __import__('os').environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_confirmed_unverified_corroboration_excludes_rejected_and_duplicates(current,other_shop,other_hash,other_status,expected):
    from hashlib import sha256
    client=create_firestore_client(Settings(gcp_project='highground-task9-tests'))
    store=PhotoStore(client,'synthetic','corroboration-'+uuid4().hex+'-')
    now=datetime.now(UTC)
    store.collection('shops').document('reporter').set(dict(lat=3.,lng=101.,is_demo=True,
        recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    data=image_bytes();digest=sha256(data).hexdigest()
    store.collection('photo_reports').document('other-report').set(dict(shop_id=other_shop,
        sha256=digest if other_hash=='same' else other_hash,evidence_status=other_status,
        corroboration_eligible=other_status!='rejected',received_at=now,confirmed_at=now,
        lat=3.,lng=101.,is_demo=True,confidence=0))
    media,*_=media_service();media.authorize=store.authorize_media
    dispatch=Dispatch();active=PhotoReportService(store,media,Assessor(current),dispatch,clock=lambda:now)
    async def run():
        photo=PhotoMedia(file_id='id',file_unique_id='unique',file_size=len(data))
        reply=await active.handle_photo(123,1,1,int(now.timestamp()),photo)
        result=await active.confirm_report_location(123,reply.report_id,at_shop=True)
        report=store.get(reply.report_id)
        if expected is None:
            assert result.code=='report_rejected' and not dispatch.events
            assert not report['corroboration_eligible']
        else:
            assert dispatch.events[0].level==expected
            assert report['corroboration_eligible']
            if expected=='warning':assert 'unverified' in dispatch.events[0].reason
    try:asyncio.run(run())
    finally:
        for name in ('shops','photo_reports','photo_pending','photo_rate'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()

@pytest.mark.skipif(not __import__('os').environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_preservation_time_counts_and_final_danger_recheck_suppresses_prompt():
    client=create_firestore_client(Settings(gcp_project='highground-task9-tests'))
    store=PhotoStore(client,'synthetic','timing-'+uuid4().hex+'-')
    shop=store.collection('shops').document('reporter')
    shop.set(dict(lat=3.,lng=101.,is_demo=True,recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    media,*_=media_service();media.authorize=store.authorize_media
    original=media.downloader.download
    async def delayed(request):
        await asyncio.sleep(.05)
        return await original(request)
    media.downloader.download=delayed
    active=PhotoReportService(store,media,Assessor(None),Dispatch())
    async def run():
        now=datetime.now(UTC)
        reply=await active.handle_photo(123,1,1,int(now.timestamp()),PhotoMedia(file_id='id',file_unique_id='unique',file_size=len(image_bytes())))
        report=store.get(reply.report_id)
        assert report['ingest_elapsed_ms']>=50
        assert report['confirmation_requested_at']>report['received_at']
        shop.update({'active_danger':True})
        guarded=await active.recheck_reply(123,reply)
        assert guarded.code=='danger' and 'photo:' not in str(guarded.reply_markup)
        assert guarded.text.endswith('Call 999 in an emergency.')
    try:asyncio.run(run())
    finally:
        for name in ('shops','photo_reports','photo_pending','photo_rate'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()

@pytest.mark.parametrize('error,expected',[('storage_unavailable','source_unavailable'),('download_unavailable','source_unavailable'),('invalid_media','invalid_photo'),('upload_too_large','upload_too_large')])
def test_ingest_error_reply_distinguishes_outage_from_invalid_upload(error,expected):
    class Store:
        def shop_for_sender(self,sender):return dict(shop_id='shop',language='en',is_demo=False,lat=3.,lng=101.)
        def begin(self,*args):return dict(report_id='id',shop_id='shop',default_lat=3.,default_lng=101.,telegram_date=datetime.now(UTC),received_at=datetime.now(UTC),is_demo=False)
        def claim(self,*args):return 'owner'
        def private(self,*args):return dict(message_id=1,file_id='id',file_unique_id='unique')
        def release(self,*args):pass
        def danger_active(self,*args):return False
    class Media:
        async def ingest_media(self,*args,**kwargs):raise MediaIngestError(error)
    active=PhotoReportService(Store(),Media(),Assessor(None),Dispatch())
    reply=asyncio.run(active.handle_photo(123,1,1,int(datetime.now(UTC).timestamp()),PhotoMedia(file_id='id',file_unique_id='unique')))
    assert reply.code==expected

@pytest.mark.parametrize('own_danger',[True,False])
@pytest.mark.skipif(not __import__('os').environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_photo_danger_invalidates_reporter_action_and_concurrent_danger_guards_reply(own_danger):
    from api.vehicle_confirmations import VehicleActionStore
    client=create_firestore_client(Settings(gcp_project='highground-task9-tests'))
    prefix='danger-'+uuid4().hex+'-';store=PhotoStore(client,'synthetic',prefix)
    shop=store.collection('shops').document('reporter')
    shop.set(dict(lat=3.,lng=101.,is_demo=True,recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    media,*_=media_service();media.authorize=store.authorize_media
    class DuringAssessment(Assessor):
        async def assess(self,*args):
            if not own_danger:shop.update({'active_danger':True})
            return self.value
    actions=VehicleActionStore(client,actions=prefix+'vehicle_actions',current=prefix+'current_vehicle_actions',shops=prefix+'shops')
    client.collection(actions.actions).document('old').set({'state':'active'})
    client.collection(actions.current).document('reporter').set({'action_id':'old'})
    dispatch=Dispatch();dispatch.vehicle_actions=actions
    model=DuringAssessment(assessment(water_location='inside_premises') if own_danger else assessment(confidence=.4))
    active=PhotoReportService(store,media,model,dispatch)
    async def run():
        now=datetime.now(UTC)
        reply=await active.handle_photo(123,1,1,int(now.timestamp()),PhotoMedia(file_id='id',file_unique_id='unique',file_size=len(image_bytes())))
        result=await active.confirm_report_location(123,reply.report_id,at_shop=True)
        assert result.code=='danger'
        assert 'photo:' not in str(result.reply_markup)
        assert shop.get().to_dict()['active_danger']
        if own_danger:
            assert client.collection(actions.actions).document('old').get().to_dict()['state']=='superseded'
            assert client.collection(actions.current).document('reporter').get().to_dict()['blocked']
            assert dispatch.events[0].reporter_shop_id=='reporter' and dispatch.events[0].level=='danger'
        else:
            assert not dispatch.events
        again=await active.handle_photo(123,2,2,int(datetime.now(UTC).timestamp()),PhotoMedia(file_id='other',file_unique_id='other'))
        assert again.code=='danger' and not again.reply_markup
    try:asyncio.run(run())
    finally:
        for name in ('shops','photo_reports','photo_pending','photo_rate','vehicle_actions','current_vehicle_actions'):
            for doc in store.collection(name).stream():doc.reference.delete()
        client.close()
