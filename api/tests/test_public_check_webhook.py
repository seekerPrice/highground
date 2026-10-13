"""Actual protected HTTP and send boundary, deterministic persistence/source doubles."""
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest
from api.config import Settings
from api.main import create_app
from api.telegram_webhook import TelegramHandler
from api.tests.test_policy_webhook import API,message,post
from api.tests.test_policy_callback_guards import Inbox
from api.tests.test_public_check_service import service
from api.tests.test_public_check_intents import transactional
from api.tests.test_public_check import NOW

class Onboarding:
    def __init__(self,pending=False):self.pending=pending;self.calls=[]
    async def waiting_location(self,sender):return self.pending
    async def process(self,*args):self.calls.append(args);return SimpleNamespace(text='Existing onboarding location',reply_markup=None,venue=None)
class Photos:
    def __init__(self):self.calls=[]
    async def pending_location_report_id(self,sender):return 'existing-photo'
    async def confirm_report_location(self,*args,**kwargs):self.calls.append((args,kwargs));return SimpleNamespace(text='Existing photo confirmation',reply_markup=None,venue=None)
    async def recheck_reply(self,sender,reply):return reply

def location(update):
    payload=message(update);payload['message']['location']={'latitude':12.3456789,'longitude':98.7654321};return payload

@pytest.mark.parametrize('race',['danger','expired','transient','onboarding_started'])
def test_public_check_last_send_guard_prevents_new_location_request_races(race):
    active,persistence,shops,reader,summary=service();shops.registered=True
    inbox=Inbox();api=API();onboarding=Onboarding()
    def hook():
        if race=='danger':shops.danger=True
        elif race=='expired':active.clock=lambda:NOW.replace(minute=10)
        elif race=='onboarding_started':onboarding.pending=True
        else:
            def fail(*args):raise OSError('Transient guard unavailable')
            shops.danger_active=fail
    inbox.hook=hook
    handler=TelegramHandler(inbox,api,onboarding=onboarding,public_check=active)
    with patch('api.public_check_store.firestore.transactional',transactional),TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),handler)) as client:
        result=post(client,message(1,'/check'))
        if race=='transient':assert result.status_code==503 and inbox.state=='retryable' and not api.sent
        else:
            assert result.status_code==200 and inbox.state=='done'
            assert not any('request_location' in button for row in (api.sent[-1][2] or {}).get('keyboard',[]) for button in row)
            if race=='danger':
                from api.alert_composer import render_danger
                assert api.sent[-1][1]==render_danger('en',False,None)[0]
            elif race=='expired':assert 'expired or finished' in api.sent[-1][1]
            else:assert 'Finish the pending' in api.sent[-1][1]

@pytest.mark.parametrize('flow',['onboarding','photo'])
def test_existing_location_confirmation_wins_without_consuming_public_intent(flow):
    active,persistence,shops,reader,summary=service();inbox=Inbox();api=API()
    onboarding=Onboarding(flow=='onboarding');photos=Photos() if flow=='photo' else None
    handler=TelegramHandler(inbox,api,onboarding=onboarding,photos=photos,public_check=active)
    with patch('api.public_check_store.firestore.transactional',transactional),TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),handler)) as client:
        # Existing intent still must not steal a newly established registration/photo context.
        active.intents.open(123,'earlier-check',NOW)
        assert post(client,location(1)).status_code==200
        assert reader.calls==summary.calls==0
        assert active.intents.active(123,NOW).status=='waiting_location'
        assert len(photos.calls if photos else onboarding.calls)==1
        inbox.state=None
        assert post(client,message(2,'/check')).status_code==200
        assert 'Finish the pending' in api.sent[-1][1]


def test_public_only_handler_unregistered_lookup_and_later_location_are_bounded():
    active,*_=service();inbox=Inbox();api=API()
    handler=TelegramHandler(inbox,api,public_check=active)
    with patch('api.public_check_store.firestore.transactional',transactional),TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),handler)) as client:
        assert post(client,message(1,'/check')).status_code==200
        inbox.state=None
        assert post(client,location(2)).status_code==200
        assert 'reports Warning' in api.sent[-1][1]
        inbox.state=None;sent=len(api.sent)
        assert post(client,location(3)).status_code==200
        assert len(api.sent)==sent and inbox.state=='done'


def test_onboarding_location_routing_read_never_creates_or_claims_registration():
    import asyncio
    from api.onboarding import Onboarding as ActualOnboarding
    class Sessions:
        def __init__(self):self.stage=None;self.reads=0
        async def get_session(self,**kwargs):
            self.reads+=1
            assert kwargs['app_name']=='highground_onboarding'
            assert kwargs['user_id']!='123' and kwargs['session_id']=='registration'
            return SimpleNamespace(state={'onboarding':{'stage':self.stage}}) if self.stage else None
        async def create_session(self,**kwargs):raise AssertionError('Public lookup must not create registration')
    sessions=Sessions();active=ActualOnboarding(None,sessions,hash_salt='synthetic',bot_username='',geocoder=None)
    async def run():
        assert not await active.waiting_location(123)
        for stage,expected in [('location',True),('confirm_location',True),('done',False),('language',False)]:
            sessions.stage=stage;assert await active.waiting_location(123) is expected
        assert sessions.reads==5
    asyncio.run(run())


def test_public_location_requires_auth_and_valid_timestamp_coordinates():
    active,*_=service();inbox=Inbox();api=API()
    with patch('api.public_check_store.firestore.transactional',transactional),TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,public_check=active))) as client:
        assert client.post('/telegram/webhook',json=message(1,'/check')).status_code==403
        bad=message(1,'/check');bad['message'].pop('date')
        assert post(client,bad).status_code==400
        malformed=location(2);malformed['message']['location']['latitude']=91.
        assert post(client,malformed).status_code==400 and not api.sent
