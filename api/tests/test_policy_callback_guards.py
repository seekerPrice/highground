"""Actual HTTP/callback send boundary with deterministic private-copy races."""
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from api.main import create_app
from api.config import Settings
from api.telegram_webhook import TelegramHandler
from api.policy_models import PolicyReply
from api.media import IngestedMedia
from api.tests.test_policy_webhook import API,callback,post

class Inbox:
    def __init__(self):self.state=None;self.hook=None
    def claim(self,*args):return ('done','owner') if self.state=='done' else ('claimed','owner')
    def transition(self,*args,**kwargs):
        self.state=args[2]
        if self.state=='sending' and self.hook:self.hook()

@pytest.mark.parametrize('race',['deleted','revoked','danger','transient'])
def test_private_copy_recheck_after_sending_prevents_races_without_false_uncertain(race):
    inbox=Inbox();api=API()
    class Policy:
        async def copy_for_sender(self,*args):return IngestedMedia(SimpleNamespace(media_id='a'*64,mime_type='application/pdf'),b'synthetic private bytes')
        async def recheck_reply(self,sender,reply):return reply
        async def recheck_copy(self,*args):
            assert inbox.state=='sending'
            if race in ('deleted','revoked'):raise PermissionError('Private copy unavailable')
            if race=='transient':raise RuntimeError('Pre-send state unavailable')
            return PolicyReply(text='Fixed Danger output',kind='danger')
    with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,policy=Policy()))) as client:
        result=post(client,callback(1,'a'*32,'copy:0'))
        assert not api.documents and len(api.acks)==1
        if race=='transient':assert result.status_code==503 and inbox.state=='retryable' and not api.sent
        else:
            assert result.status_code==200 and inbox.state=='done'
            assert len(api.sent)==(1 if race=='danger' else 0)


def test_private_document_transport_is_bounded_multipart_without_url_or_original_filename():
    import httpx
    from api.tools.telegram import TelegramAPI
    seen=[]
    def transport(request):
        assert request.url.path.endswith('/sendDocument')
        seen.append(request.content)
        return httpx.Response(200,json={'ok':True,'result':{'message_id':42}})
    api=TelegramAPI('synthetic',httpx.MockTransport(transport))
    assert api.send_document(123,b'synthetic document','application/pdf','policy-page-1.pdf')==42
    assert b'filename="policy-page-1.pdf"' in seen[0] and b'synthetic document' in seen[0]
    with pytest.raises(ValueError):api.send_document(123,b'a'*20_000_001,'application/pdf','policy-page-1.pdf')
    with pytest.raises(ValueError):api.send_document(123,b'a','application/pdf','../../private.pdf')
