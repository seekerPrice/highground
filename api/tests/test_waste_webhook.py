"""Real HTTP routing and the last property-prompt send boundary, fake persistence."""
from fastapi.testclient import TestClient
import pytest
from api.main import create_app
from api.config import Settings
from api.telegram_webhook import TelegramHandler
from api.waste_service import WasteService
from api.tests.test_policy_callback_guards import Inbox
from api.tests.test_policy_webhook import API,message,post

class Store:
    def __init__(self):self.current=True;self.danger=False;self.error=False;self.confirmed=[];self.owner=True
    def shop_for_sender(self,sender):return dict(shop_id='shop',language='en',is_demo=False,lat=3.,lng=101.) if sender in (123,456) else None
    def owner_shop(self,sender):return self.shop_for_sender(sender) if sender==123 and self.owner else None
    def danger_active(self,identity):return self.danger
    def action(self,identity,sender):
        if self.error:raise OSError('Transient pre-send read')
        if sender!=123 or not self.owner:raise PermissionError()
        if not self.current:raise ValueError('No longer current')
        return dict(action_id=identity,kind='donation',item_name='Synthetic sealed item',available=False)
    def confirm(self,identity,sender,**kwargs):self.action(identity,sender);self.confirmed.append(kwargs)
    def stage_street(self,sender,label,operation):
        if sender!=123 or not self.owner:raise PermissionError()
        return dict(action_id='a'*32,label=label,kind='street')

@pytest.mark.parametrize('race',['owner_removed','baseline_refreshed','danger','transient'])
def test_actual_owner_prompt_final_send_rechecks_current_action_and_danger(race):
    store=Store();service=WasteService(store);inbox=Inbox();api=API()
    def hook():
        if race=='owner_removed':store.owner=False
        elif race=='baseline_refreshed':store.current=False
        elif race=='danger':store.danger=True
        else:store.error=True
    inbox.hook=hook
    with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,waste=service))) as client:
        result=post(client,message(1,'/start donate_'+'a'*32))
        if race=='transient':assert result.status_code==503 and inbox.state=='retryable' and not api.sent
        else:
            assert result.status_code==200 and inbox.state=='done' and len(api.sent)==1
            assert api.sent[0][2] is None
            if race=='danger':
                from api.alert_composer import render_danger
                assert api.sent[0][1]==render_danger('en',False,None)[0]
            else:assert 'This action is unavailable' in api.sent[0][1]


def test_callback_ack_denial_replay_and_no_property_prompt_at_worker_danger():
    store=Store();service=WasteService(store);inbox=Inbox();api=API()
    with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,waste=service))) as client:
        payload=dict(update_id=1,callback_query=dict(id='synthetic',**{'from':{'id':456}},message=dict(message_id=10,chat=dict(id=456,type='private')),data='waste:donate:'+'a'*32))
        assert post(client,payload).status_code==200 and len(api.acks)==1 and not store.confirmed
        assert post(client,payload).status_code==200 and len(api.acks)==1
    inbox.state=None;store.danger=True
    with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,waste=service))) as client:
        payload=message(2,'/street Jalan Example');payload['message']['chat']['id']=456
        assert post(client,payload).status_code==200
        from api.alert_composer import render_danger
        assert api.sent[-1][1]==render_danger('en',False,None)[0] and api.sent[-1][2] is None


def test_street_instructions_require_owner_at_final_send_even_without_action():
    store=Store();service=WasteService(store);inbox=Inbox();api=API()
    inbox.hook=lambda:setattr(store,'owner',False)
    with TestClient(create_app(Settings(telegram_webhook_secret='synthetic-secret'),TelegramHandler(inbox,api,waste=service))) as client:
        assert post(client,message(1,'/street')).status_code==200
        assert 'This action is unavailable' in api.sent[0][1]
        assert '/street followed' not in api.sent[0][1] and api.sent[0][2] is None
