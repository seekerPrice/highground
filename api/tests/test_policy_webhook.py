"""Actual protected webhook/Firestore; document/model sends are in-process fakes."""
from datetime import UTC,datetime
from types import SimpleNamespace
from fastapi.testclient import TestClient
from api.config import Settings
from api.main import create_app
from api.telegram_webhook import TelegramHandler
from api.telegram_inbox import FirestoreInbox
from api.tools.telegram import TelegramSendError
from api.photo_store import PhotoStore
from api.tests.test_policy_service import policy

class API:
    def __init__(self):self.sent=[];self.documents=[];self.acks=[];self.reject=False
    def send_message(self,sender,text,reply_markup=None):
        if self.reject:raise TelegramSendError(uncertain=True)
        self.sent.append((sender,text,reply_markup));return len(self.sent)+100
    def answer_callback_query(self,*args):self.acks.append(args)
    def send_document(self,*args):self.documents.append(args);return 200

def message(update,text=None,photo=False,document=False):
    value={'update_id':update,'message':{'message_id':update,'date':int(datetime.now(UTC).timestamp()),'chat':{'id':123,'type':'private'}}}
    if text:value['message']['text']=text
    if photo:value['message']['photo']=[dict(file_id='image',file_unique_id='image',width=8,height=8)]
    if document:value['message']['document']=dict(file_id='pdf',file_unique_id='pdf',mime_type='application/pdf')
    return value

def post(client,payload):return client.post('/telegram/webhook',json=payload,headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic-secret'})
def callback(update,identity,action,sender=123):
    return {'update_id':update,'callback_query':{'id':str(update),'from':{'id':sender},'message':{'message_id':100,'chat':{'id':sender,'type':'private'}},'data':f'policy:{action.split(":")[0]}:{identity}'+(':'+action.split(':')[1] if ':' in action else '')}}

def create(policy,photos=None):
    active,store,*_=policy;api=API();inbox=FirestoreInbox(store.client,store.prefix+'inbox')
    handler=TelegramHandler(inbox,api,photos=photos,policy=active)
    return TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),handler)),api,inbox

def cleanup(store):
    for name in ('inbox','photo_reports','photo_pending','photo_rate'):
        for row in store.collection(name).stream(timeout=5,retry=None):row.reference.delete(timeout=5,retry=None)

def test_public_disclosure_before_upload_owner_keep_photos_done_private_copy_delete(policy):
    active,store,gateway,model=policy;client,api,inbox=create(policy)
    try:
        with client:
            assert client.post('/telegram/webhook',json=message(1,'/policy')).status_code==403
            assert post(client,message(1,'/policy')).status_code==200
            job=store.current(123);assert job['disclosed'] and not job['choice_frozen']
            assert post(client,callback(2,job['intake_id'],'keep')).status_code==200
            assert post(client,message(3,photo=True)).status_code==200 and model.calls==0
            assert post(client,callback(4,job['intake_id'],'done')).status_code==200
            result=store.get(job['intake_id']);assert result['status']=='complete' and result['choice']=='keep'
            assert post(client,callback(5,job['intake_id'],'copy:0',456)).status_code==200 and not api.documents
            assert post(client,callback(6,job['intake_id'],'copy:0')).status_code==200 and len(api.documents)==1
            assert post(client,callback(7,job['intake_id'],'delete')).status_code==200 and not gateway.objects
            assert post(client,callback(8,job['intake_id'],'copy:0')).status_code==200 and len(api.documents)==1
            assert all(len(button['callback_data'].encode())<=64 for _,_,markup in api.sent if markup for row in markup['inline_keyboard'] for button in row)
    finally:cleanup(store)

def test_ambiguous_notice_send_does_not_authorize_original_retention(policy):
    active,store,gateway,model=policy;client,api,inbox=create(policy)
    try:
        with client:
            api.reject=True;assert post(client,message(1,'/policy')).status_code==200
            job=store.current(123);assert not job['disclosed']
            api.reject=False;assert post(client,message(2,photo=True)).status_code==200
            assert gateway.calls==0 and not job['originals']
            assert post(client,message(3,'/policy')).status_code==200
            assert store.current(123)['disclosed']
    finally:cleanup(store)

class FloodPhotos:
    def __init__(self,store):self.store=store;self.calls=0;self.fail=True
    async def handle_photo(self,sender,update,message_id,sent,photo,processing_started_at=None):
        self.calls+=1;shop=self.store.shop_for_sender(sender)
        record=self.store.begin(shop,sender,message_id,datetime.fromtimestamp(sent,UTC),photo,processing_started_at)
        return SimpleNamespace(text='Original flood-photo response',reply_markup=None,venue=None,report_id=record['report_id'])
    async def recheck_reply(self,sender,reply):
        if self.fail:self.fail=False;raise RuntimeError('Transient pre-send guard failure')
        return reply
    async def bound_photo_report(self,sender,message_id,unique):return self.store.bound_photo_report(sender,message_id,unique)

def test_old_retryable_flood_photo_binding_wins_over_new_policy_intake(policy):
    active,store,gateway,model=policy
    photos=FloodPhotos(PhotoStore(store.client,store.hash_salt,store.prefix))
    client,api,inbox=create(policy,photos)
    original=message(1,photo=True)
    try:
        with client:
            assert post(client,original).status_code==503 and photos.calls==1
            assert post(client,message(2,'/policy')).status_code==200
            assert post(client,original).status_code==200
            assert photos.calls==2 and gateway.calls==0
            assert not store.current(123)['uploads']
            # New, unbound photo is explicitly in policy context.
            assert post(client,message(3,photo=True)).status_code==200 and gateway.calls==1
    finally:cleanup(store)

def test_worker_policy_commands_are_bounded_denials_and_fixed_danger_has_no_capture(policy):
    from api.alert_composer import render_danger
    active,store,gateway,model=policy;client,api,inbox=create(policy)
    try:
        with client:
            for number,command in enumerate(('/policy','/policy done','/policy cancel'),20):
                payload=message(number,command);payload['message']['chat']['id']=456
                assert post(client,payload).status_code==200
                assert 'Only the registered shop owner' in api.sent[-1][1]
            assert not gateway.calls and not model.calls and store.current(123) is None
            store.collection('shops').document('shop').update({'active_danger':True})
            payload=message(30,'/policy');payload['message']['chat']['id']=456
            assert post(client,payload).status_code==200
            expected,markup=render_danger('en',True,None)
            assert api.sent[-1][1]==expected and api.sent[-1][2]==markup
            assert not gateway.calls and not model.calls
    finally:cleanup(store)
