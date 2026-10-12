"""Public regression coverage for cold guards and receipt-only recovery media."""
import asyncio
from datetime import UTC,datetime
from hashlib import sha256
import os
from pathlib import Path
from uuid import uuid4
import httpx
import pytest
from api.config import Settings
from api.tools.firestore import create_firestore_client
from api.report_store import ReportStore
from api.active_risk import ActiveRiskStore
from api.media_store import MediaStore
from api.media import MediaService
from api.media_models import MediaRequest,MediaIngestError
from api.recovery import RecoveryService,LazyRecoveryService
from api.telegram_webhook import TelegramHandler
from api.telegram_inbox import FirestoreInbox
from api.inventory_models import InventoryReply
from api.main import create_app
from api.report_api import ReportReader
from api.i18n import danger_text
from api.tests.test_reports import BASE,loss
from api.tests.test_inventory import VIDEO,video
from api.tests.test_media import image_bytes,Ledger

pytestmark=pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')

class Bot:
    def __init__(self):self.messages=[]
    def send_message(self,chat,text,reply_markup=None):
        self.messages.append(dict(text=text,reply_markup=reply_markup));return len(self.messages)

@pytest.mark.parametrize('danger',[False,True])
def test_public_cold_recovery_guard_does_not_construct_media_dependencies(monkeypatch,danger):
    from api.tools import cloud_events,storage
    project='cold-guard-'+uuid4().hex[:16];settings=Settings(gcp_project=project,gcs_bucket='synthetic',hash_salt='synthetic',telegram_bot_token='synthetic',telegram_webhook_secret='synthetic',official_max_age_minutes=7)
    client=create_firestore_client(settings);inbox=FirestoreInbox(client,'inbox');bot=Bot();constructions=[]
    client.collection('shops').document('shop').set(dict(lat=3.,lng=101.,is_demo=True,active_danger=danger,recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
    def unavailable(settings):constructions.append('event_sinks');raise OSError('Injected analytics factory failure')
    def storage_client(settings):constructions.append('storage');return object()
    monkeypatch.setattr(cloud_events,'create_event_sinks',unavailable)
    monkeypatch.setattr(storage,'create_storage_client',storage_client)
    class Onboarding:
        async def process(self,*args):return InventoryReply(text='Ordinary onboarding reply',kind='prompt')
    lazy=LazyRecoveryService(settings);handler=TelegramHandler(inbox,bot,Onboarding(),recovery=lazy);app=create_app(settings,handler)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as http:
            response=await http.post('/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'},json=dict(update_id=1,message=dict(message_id=1,date=int(datetime.now(UTC).timestamp()),chat=dict(id=123,type='private'),text='/start')))
        assert response.status_code==200
        assert len(bot.messages)==1 and constructions==[] and lazy.active is None
        assert bot.messages[0]['text']==(danger_text('en',is_demo=True) if danger else 'Ordinary onboarding reply')
    try:asyncio.run(run())
    finally:
        for name in ('shops','inbox'):
            for doc in client.collection(name).stream():doc.reference.delete()
        client.close()

class Originals:
    def __init__(self):self.values={};self.fail_reads=set()
    def uri(self,identity):return 'gs://synthetic/originals/'+identity
    def create_original(self,identity,data,mime,digest):
        assert identity not in self.values or self.values[identity]==data
        self.values[identity]=data
    def read_original(self,identity):
        if identity in self.fail_reads:raise MediaIngestError('storage_unavailable')
        return self.values[identity]

class RecoveryHarness:
    def __init__(self):
        self.settings=Settings(gcp_project='highground-review-tests',telegram_webhook_secret='synthetic');self.client=create_firestore_client(self.settings);self.prefix='review-'+uuid4().hex+'-'
        self.store=ReportStore(self.client,'synthetic',self.prefix,risks=ActiveRiskStore(self.client,risks=self.prefix+'active_risks',shops=self.prefix+'shops',current_actions=self.prefix+'current_vehicle_actions'));self.records=MediaStore(self.client,'synthetic',self.prefix+'media');self.originals=Originals();self.ledger=Ledger();self.bot=Bot();self.next_update=0;self.neighbours=[];self.date=int(datetime.now(UTC).timestamp())-1
        self.files={'baseline':VIDEO,'early':VIDEO,'later':(Path(__file__).parents[2]/'demo/media/synthetic-after-still.mp4').read_bytes(),'photo':image_bytes()};self.ingest_hook=None
        harness=self
        class Download:
            async def download(self,request):
                if harness.ingest_hook:harness.ingest_hook(request)
                return harness.files[request.file_id]
        class Assessor:
            calls=[]
            async def assess(self,media,*args):self.calls.append(media.record.media_id);return loss()
        class OtherMedia:
            async def handle_video(self,*args,**kwargs):harness.neighbours.append('baseline');return InventoryReply(text='Wrong baseline route',kind='prompt')
            async def handle_photo(self,*args,**kwargs):harness.neighbours.append('neighbour');return InventoryReply(text='Wrong neighbour route',kind='prompt')
            async def recheck_reply(self,sender,reply):return reply
        self.model=Assessor();self.media=MediaService(self.records,Download(),self.originals,self.ledger,self.store.authorize_media)
        self.recovery=RecoveryService(self.store,self.media,self.model,web_base_url='http://localhost:3000')
        self.inbox=FirestoreInbox(self.client,self.prefix+'inbox');self.app=create_app(self.settings,TelegramHandler(self.inbox,self.bot,inventory=OtherMedia(),photos=OtherMedia(),recovery=self.recovery))
    async def initialize(self):
        self.shop=self.store.collection('shops').document('shop');self.shop.set(dict(shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,baseline_inventory_id='baseline',recipients=[dict(telegram_chat_id=123,language='en',role='owner')]))
        baseline=await self.media.ingest_media(MediaRequest(shop_id='shop',kind='baseline_video',sender_chat_id=123,message_id=0,file_id='baseline',file_unique_id='baseline',declared_size=len(VIDEO),declared_mime='video/mp4',received_at=datetime.now(UTC),telegram_date=datetime.fromtimestamp(self.date,UTC),lat=3.,lng=101.,location_attribution='confirmed_shop',is_demo=True))
        self.store.collection('inventories').document('baseline').set(dict(BASE,media_id=baseline.record.media_id,shop_id='shop'))
    async def send(self,message_id,**values):
        self.next_update+=1
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://test') as http:
            response=await http.post('/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic'},json=dict(update_id=self.next_update,message=dict(message_id=message_id,date=self.date,chat=dict(id=123,type='private'),**values)))
        assert response.status_code==200
        return self.bot.messages[-1]
    def video(self,identity):return video().model_copy(update={'file_id':identity,'file_unique_id':identity,'file_size':len(self.files[identity])}).model_dump()
    def photo(self):return [dict(file_id='photo',file_unique_id='photo',file_size=len(self.files['photo']),width=4,height=4)]
    def uploaded(self,kind):return [self.records.get(doc.id).model_dump() for doc in self.store.collection('media').stream() if doc.to_dict()['kind']==kind]
    def close(self):
        for name in ('shops','inventories','media','inbox','recovery_jobs','recovery_current','recovery_private','recovery_intents','recovery_uploads','active_risks','current_vehicle_actions'):
            for doc in self.store.collection(name).stream():doc.reference.delete()
        self.client.close()

@pytest.mark.parametrize('danger',[False,True])
def test_public_predeclaration_photo_preserves_original_and_late_replay(danger):
    h=RecoveryHarness()
    async def run():
        await h.initialize()
        if danger:h.shop.update({'active_danger':True})
        await h.send(1,text='/report');original=h.store.current(123)['report_id']
        reply=await h.send(2,photo=h.photo())
        records=h.uploaded('waterline_photo')
        assert len(records)==1 and records[0]['sha256']==sha256(h.files['photo']).hexdigest()
        assert records[0]['ledger_status']=='done' and h.originals.values[records[0]['media_id']]==h.files['photo']
        assert h.store.current(123)['status']=='awaiting_declaration' and h.model.calls==[]
        if danger:assert reply['text']==danger_text('en',is_demo=True)
        await h.send(3,text='/cancel')
        await h.send(2,photo=h.photo())
        assert h.store.resolve_context(123,2,'photo')['report_id']==original and h.neighbours==[]
        assert len(h.ledger.ids)==2 and h.uploaded('waterline_photo')[0]==records[0]
        assert h.shop.get().to_dict()['baseline_inventory_id']=='baseline'
    try:asyncio.run(run())
    finally:h.close()

@pytest.mark.parametrize('danger_phase',['none','known','during_ingest','after_selection'])
def test_public_receipt_video_then_declaration_new_clip_and_late_replay(danger_phase):
    h=RecoveryHarness()
    async def run():
        await h.initialize();await h.send(1,text='/report');original=h.store.current(123)['report_id'];frozen=h.store.current(123)['baseline']
        if danger_phase in ('during_ingest','after_selection'):
            await h.send(2,text='/report confirm')
            if danger_phase=='during_ingest':
                h.ingest_hook=lambda request:h.shop.update({'active_danger':True}) if request.kind=='after_video' else None
            else:
                original_select=h.store.select_upload
                def selection_race(*args,**kwargs):
                    selected=original_select(*args,**kwargs)
                    if args[4]=='early':h.shop.update({'active_danger':True})
                    return selected
                h.store.select_upload=selection_race
        elif danger_phase=='known':h.shop.update({'active_danger':True})
        early=await h.send(3,video=h.video('early'));early_record=h.uploaded('after_video')[0]
        assert h.model.calls==[] and early_record['ledger_status']=='done'
        if danger_phase!='none':assert early['text']==danger_text('en',is_demo=True)
        h.ingest_hook=None
        if danger_phase!='none':h.store.risk_store.reset_demo('shop')
        # Mutable registration cannot change the already frozen report comparison.
        h.shop.update({'lat':4.,'lng':102.,'baseline_inventory_id':'different'})
        await h.send(4,text='/report confirm')
        new=await h.send(5,video=h.video('later'))
        assert '#key=' in new['text'] and len(h.model.calls)==1
        job=h.store.current(123);assert job['report_id']==original and job['baseline']==frozen and job['upload']['message_id']==5
        later=next(r for r in h.uploaded('after_video') if r['media_id']==job['media_id'])
        assert (later['lat'],later['lng'])==(3.,101.)
        report=ReportReader(h.store,h.records,h.originals).report(original,'Bearer '+h.store.token(original))
        assert report.assessment_media_id==later['media_id'] and report.assessment_media_id!=early_record['media_id']
        assert sum(e.media_id==report.assessment_media_id and e.kind=='after_video' for e in report.evidence)==1
        assert sum(e.kind=='after_video' for e in report.evidence)==2
        assert any(row.evidence_timestamp_s is not None for row in report.items)
        await h.send(5,video=h.video('later'))
        assert len(h.model.calls)==1
        await h.send(6,text='/cancel')
        await h.send(3,video=h.video('early'))
        assert h.store.resolve_context(123,3,'early')['report_id']==original and h.neighbours==[] and len(h.model.calls)==1
        assert next(r for r in h.uploaded('after_video') if r['media_id']==early_record['media_id'])==early_record
        assert len(h.ledger.ids)==3 and h.shop.get().to_dict()['baseline_inventory_id']=='different'
        # A storage outage on an old receipt replay cannot downgrade the report.
        h.originals.fail_reads.add(early_record['media_id'])
        await h.send(3,video=h.video('early'))
        completed=h.store.collection('recovery_jobs').document(original).get().to_dict()
        assert completed['status']=='complete' and completed['assessment']==job['assessment'] and completed['upload']==job['upload']
        with pytest.raises(MediaIngestError):
            h.store.preserve_receipt_only(original,'stale-owner',123,5,'later')
        h.store.preserve_receipt_only(original,completed['owner'],123,5,'later')
        protected=h.store.collection('recovery_jobs').document(original).get().to_dict()
        assert protected['upload']==job['upload'] and protected['assessment']==job['assessment']
        assert h.store.upload_reference(123,5,'later').get().to_dict()['receipt_only'] is False
    try:asyncio.run(run())
    finally:h.close()


@pytest.mark.parametrize('bad_selection',['missing','unknown','wrong_kind','malformed','not_receipted'])
def test_report_reader_fails_closed_on_invalid_assessment_media_selection(bad_selection):
    h=RecoveryHarness()
    async def run():
        await h.initialize();await h.send(1,text='/report');await h.send(2,text='/report confirm');await h.send(3,video=h.video('later'))
        job=h.store.current(123);ref=h.store.collection('recovery_jobs').document(job['report_id']);selected=job['media_id']
        from google.cloud import firestore
        changes={
            'missing':{'media_id':firestore.DELETE_FIELD},
            'unknown':{'media_id':'f'*64},
            'wrong_kind':{'media_id':job['baseline']['media_id']},
            'malformed':{'media_id':'not-a-media-id'},
            'not_receipted':{'evidence_media_ids':[job['baseline']['media_id']]},
        }
        ref.update(changes[bad_selection])
        with pytest.raises((ValueError,KeyError)):
            ReportReader(h.store,h.records,h.originals).report(job['report_id'],'Bearer '+h.store.token(job['report_id']))
        assert h.records.get(selected).sha256==sha256(h.files['later']).hexdigest()
    try:asyncio.run(run())
    finally:h.close()
