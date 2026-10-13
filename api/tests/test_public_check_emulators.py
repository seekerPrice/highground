"""Actual Firestore/protected HTTP with virtual Telegram and source/model doubles."""
import asyncio,os
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from api.config import Settings
from api.tools.firestore import create_firestore_client
from api.photo_store import PhotoStore
from api.active_risk import ActiveRiskStore
from api.public_check_store import FirestoreCheckIntentStore
from api.public_check_service import PublicCheckService
from api.telegram_inbox import FirestoreInbox
from api.telegram_webhook import TelegramHandler
from api.main import create_app
from api.tests.test_policy_webhook import API,message,post
from api.tests.test_public_check_webhook import location
from api.tests.test_public_check_service import Reader,Summary
from api.tests.test_public_check import NOW

pytestmark=pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')


def test_actual_public_webhook_late_original_replay_keeps_new_intent_and_no_signup():
    client=create_firestore_client(Settings(gcp_project='highground-check-service-tests'));prefix='check-service-'+uuid4().hex+'-'
    risks=ActiveRiskStore(client,shops=prefix+'shops',risks=prefix+'risks')
    shops=PhotoStore(client,'synthetic',prefix,risks=risks)
    intents=FirestoreCheckIntentStore(client,'synthetic',intents=prefix+'intents',senders=prefix+'senders',operations=prefix+'operations')
    reader=Reader();summary=Summary()
    class Service(PublicCheckService):
        fail=True
        async def recheck_reply(self,sender,reply,**kwargs):
            reply=await super().recheck_reply(sender,reply,**kwargs)
            if self.fail and getattr(reply,'intent_id',None) and not reply.location_request:
                self.fail=False;raise OSError('Transient final guard before transport')
            return reply
    active=Service(shops,intents,reader,summary,clock=lambda:NOW)
    api=API();inbox=FirestoreInbox(client,prefix+'inbox');handler=TelegramHandler(inbox,api,public_check=active)
    try:
        with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),handler)) as http:
            assert post(http,message(1,'/check')).status_code==200
            original=location(2)
            assert post(http,original).status_code==503 and reader.calls==summary.calls==1
            assert post(http,message(3,'/check')).status_code==200
            current=intents.active(123,NOW)
            assert current.status=='waiting_location'
            assert post(http,original).status_code==200
            assert 'expired or finished' in api.sent[-1][1]
            assert intents.active(123,NOW).intent_id==current.intent_id and reader.calls==summary.calls==1
            assert not list(client.collection(prefix+'shops').stream(timeout=5,retry=None))
            state=[doc.to_dict() for name in ('intents','senders','operations','inbox') for doc in client.collection(prefix+name).stream(timeout=5,retry=None)]
            serialized=str(state)
            assert '12.3456789' not in serialized and '98.7654321' not in serialized
            assert "'lat'" not in serialized and "'lng'" not in serialized
            assert len(list(client.collection(prefix+'operations').stream(timeout=5,retry=None)))==1
            assert len(list(client.collection(prefix+'intents').stream(timeout=5,retry=None)))==2
            assert all(len(button.get('callback_data','').encode())<=64 for _,_,markup in api.sent if markup for row in markup.get('inline_keyboard',[]) for button in row)
    finally:
        try:
            asyncio.run(active.close())
            for name in ('intents','senders','operations','inbox','shops','risks'):
                for doc in client.collection(prefix+name).stream(timeout=5,retry=None):doc.reference.delete(timeout=5,retry=None)
        finally:client.close()
