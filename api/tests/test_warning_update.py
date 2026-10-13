"""Optional Warning update button is owner-bound and rechecks Danger before sending."""
import asyncio
from types import SimpleNamespace
import pytest
from api.alert_composer import AlertComposer, render_danger
from api.inventory import InventoryService
from api.telegram_webhook import TelegramHandler, Update, WebhookRetry
from api.tests.test_dispatch import NOW, shop
from api.i18n import text

class Inbox:
    def __init__(self,hook=None):self.states={};self.hook=hook
    def claim(self,identity,*args):return (self.states.get(identity,'claimed'),'owner')
    def transition(self,identity,owner,state,**kwargs):
        self.states[identity]=state
        if state=='sending' and self.hook:self.hook()

class Store:
    def __init__(self):self.danger=False;self.role='owner';self.present=True;self.failed=False
    def shop_for_sender(self,sender):
        if self.failed:raise ConnectionError('registry unavailable')
        if not self.present:return None
        return dict(shop_id='ordinary',language='en',is_demo=True,lat=3.,lng=101.,recipients=[dict(telegram_chat_id=9,role=self.role)])
    def danger_active(self,identity):return self.danger

class API:
    def __init__(self):self.sent=[]
    def answer_callback_query(self,*args):pass
    def send_message(self,chat_id,body,**kwargs):self.sent.append((body,kwargs));return 55

def callback():return Update.model_validate(dict(update_id=5,callback_query={'id':'update','from':{'id':9},'message':{'message_id':8,'chat':{'id':9,'type':'private'}},'data':'inventory:refresh'}))


def test_warning_button_is_localized_and_absent_from_watch_and_danger():
    for language in ('en','ms','zh','ta','bn','ne','my','id'):
        for level in ('watch','warning','danger'):
            event=dict(event_id='event',created_at=NOW,lat=3.,lng=101.,level=level,is_demo=True)
            _,_,markup=asyncio.run(AlertComposer().compose(event,shop(),language))
            buttons=[b for row in (markup or {}).get('inline_keyboard',[]) for b in row if b.get('callback_data')=='inventory:refresh']
            assert len(buttons)==(1 if level=='warning' else 0)
            if buttons:assert buttons[0]['text']==text(language,'video_update_optional')


@pytest.mark.parametrize('race',[None,'danger','worker','removed','failure'])
def test_warning_callback_owner_guard_final_recheck_and_retry(race):
    store=Store();api=API()
    def change():
        if race=='danger':store.danger=True
        elif race=='worker':store.role='worker'
        elif race=='removed':store.present=False
        elif race=='failure':store.failed=True
    inbox=Inbox(change);handler=TelegramHandler(inbox,api,inventory=InventoryService(store,None,None))
    async def run():
        if race=='failure':
            with pytest.raises(WebhookRetry):await handler.handle(callback())
            assert inbox.states[5]=='retryable' and not api.sent
            return
        assert await handler.handle(callback())=='done'
        assert await handler.handle(callback())=='done'
        assert len(api.sent)==1
        body,kwargs=api.sent[0]
        if race=='danger':assert body==render_danger('en',True)[0]
        elif race in ('worker','removed'):assert text('en','inventory_request') not in body
        else:assert text('en','inventory_request') in body
    asyncio.run(run())


def test_worker_button_does_not_request_video_or_exit_recovery():
    store=Store();store.role='worker';api=API()
    async def never(*args):raise AssertionError('Worker must not change recovery flow')
    handler=TelegramHandler(Inbox(),api,inventory=InventoryService(store,None,None),recovery=SimpleNamespace(exit=never))
    asyncio.run(handler.handle(callback()))
    assert len(api.sent)==1 and text('en','inventory_request') not in api.sent[0][0]
