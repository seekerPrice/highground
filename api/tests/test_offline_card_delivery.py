"""Card public delivery against real Firestore storage, without external sends."""
import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import patch
import pytest
from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore
from api.offline_card_store import FirestoreCardStore
from api.offline_card_service import OfflineCardService
from api.destinations import SafePoint
from api.tests.test_offline_card import context

class Risk:
    def get(self,shop):return SimpleNamespace(active_danger=False,episode_id=None)
    def claim_delivery(self,shop,event):return 'claimed','risk-owner'
    def release_delivery(self,shop,owner):pass

class Assets:
    def write(self,identity,data):self.data=data;return 'derived/cards/'+identity+'.png','f'*64
    def read(self,path,digest):return self.data

class Telegram:
    def __init__(self):self.photos=[]
    def send_photo(self,chat,data,caption):self.photos.append((chat,data,caption));return 17

@pytest.mark.skipif(not os.getenv('FIRESTORE_EMULATOR_HOST'),reason='Firestore required')
def test_persisted_nonempty_card_and_sourced_destinations_deliver_once():
    asyncio.run(persisted_delivery())

async def persisted_delivery():
    client=firestore.Client(project='highground-card-test',credentials=AnonymousCredentials())
    prefix='card_'+uuid4().hex+'_'
    store=FirestoreCardStore(client,collection=prefix+'cards',shops=prefix+'shops')
    points=json.loads(Path('infra/data/safe_points.json').read_text())
    if isinstance(points,dict):points=points['safe_points']
    parking=SafePoint.model_validate(next(p for p in points if p['type']=='parking'))
    shelter=SafePoint.model_validate(next(p for p in points if p['type']=='pps'))
    card=context(parking=parking,shelter=shelter)
    bot=Telegram();assets=Assets()
    service=OfflineCardService(store,bot,Risk(),None,None,None,lambda:assets,hash_salt='isolated-test')
    event={'event_id':card.card_id,'is_demo':True,'level':'watch','source':'demo','created_at':card.prepared_at,'scenario_generation':0}
    try:
        store.begin(card,101,event)
        persisted=store.get(card.card_id)
        assert isinstance(persisted['context']['items'],list)
        with patch('api.offline_card_service.render_offline_card',return_value=b'PNG test bytes'):
            assert await service.deliver(card.card_id)=='accepted'
            assert await service.deliver(card.card_id)=='accepted'
        assert len(bot.photos)==1 and bot.photos[0][0]==101
        assert store.get(card.card_id)['status']=='accepted'
        replay=await service._freeze(card.card_id,{},'en',event)
        assert replay==card and replay.parking==parking and replay.shelter==shelter
    finally:
        try:
            for snapshot in client.collection(store.collection).stream(timeout=8,retry=None):snapshot.reference.delete(timeout=8,retry=None)
        finally:client.close()


def test_owner_card_is_not_limited_to_operator_fixture_scope_but_reset_still_fences():
    from api.demo_scenario import event_is_current
    scenario={'state':'ready','generation':3,'fixture_shop_ids':['demo-t16-1']}
    demand={'source':'card_request','is_demo':True,'scenario_generation':3}
    assert event_is_current(demand,scenario,'ordinary-synthetic-owner')
    assert not event_is_current(demand,dict(scenario,generation=4),'ordinary-synthetic-owner')
    assert not event_is_current(demand,dict(scenario,state='resetting'),'ordinary-synthetic-owner')
    assert not event_is_current(dict(demand,source='demo'),scenario,'ordinary-synthetic-owner')


def test_photo_transport_sends_bounded_png_multipart_and_redacts_token(caplog):
    import httpx,logging
    from api.tools.telegram import TelegramAPI
    requests=[]
    def handle(request):
        requests.append(request)
        return httpx.Response(200,json={'ok':True,'result':{'message_id':29}})
    bot=TelegramAPI('123:PRIVATE',httpx.MockTransport(handle))
    caplog.set_level(logging.INFO,logger='httpx')
    assert bot.send_photo(101,b'\x89PNG\r\n\x1a\nimage','Save this image')==29
    request=requests[0];body=request.content
    assert request.url.path.endswith('/sendPhoto')
    assert 'multipart/form-data; boundary=' in request.headers['content-type']
    assert b'name="chat_id"' in body and b'101' in body
    assert b'name="caption"' in body and b'Save this image' in body
    assert b'name="photo"; filename="offline-card.png"' in body and b'Content-Type: image/png' in body
    assert b'\x89PNG\r\n\x1a\nimage' in body and b'123:PRIVATE' not in body
    assert '123:PRIVATE' not in caplog.text
    with pytest.raises(ValueError):bot.send_photo(101,b'x'*10_000_001,'x')
    with pytest.raises(ValueError):bot.send_photo(101,b'not png','x')
    with pytest.raises(ValueError):bot.send_photo(101,b'\x89PNG\r\n\x1a\nimage','x'*1025)

class MemoryStore:
    def __init__(self,card):
        self.record={'card_id':card.card_id,'context':card.model_dump(),'chat_id':101,'event':{'event_id':card.card_id,'source':'card_request','level':'watch','is_demo':True,'scenario_generation':0,'created_at':card.prepared_at},'status':'pending'}
        self.scenario_value={'state':'ready','generation':0,'fixture_shop_ids':['unrelated-fixture']}
    def get(self,identity):return dict(self.record)
    def scenario(self):return self.scenario_value
    def claim(self,identity):
        status=self.record['status']
        if status in ('accepted','uncertain','superseded','virtual_skipped'):return status,None
        self.record.update(status='preparing');return 'claimed','owner'
    def update(self,identity,owner,**fields):self.record.update(fields)

class MutableRisk(Risk):
    danger=False
    def get(self,shop):return SimpleNamespace(active_danger=self.danger,episode_id=None)


def test_final_danger_and_reset_guards_block_optional_photo_after_render():
    async def run(reset):
        card=context();store=MemoryStore(card);risk=MutableRisk();bot=Telegram();assets=Assets()
        def render(*args):
            if reset:store.scenario_value['generation']=1
            else:risk.danger=True
            return b'\x89PNG\r\n\x1a\nimage'
        service=OfflineCardService(store,bot,risk,None,None,None,lambda:assets,hash_salt='test')
        with patch('api.offline_card_service.render_offline_card',side_effect=render):assert await service.deliver(card.card_id)=='superseded'
        assert not bot.photos and store.record['status']=='superseded'
    asyncio.run(run(False));asyncio.run(run(True))


def test_initial_danger_never_constructs_card_model_or_asset_and_uncertain_is_terminal():
    async def run():
        from api.tools.telegram import TelegramSendError
        card=context();store=MemoryStore(card);risk=MutableRisk();risk.danger=True;bot=Telegram()
        async def selector(context):raise AssertionError('Danger cannot select wording')
        def assets():raise AssertionError('Danger cannot construct image storage')
        service=OfflineCardService(store,bot,risk,None,None,selector,assets,hash_salt='test')
        assert await service.deliver(card.card_id)=='superseded' and not bot.photos
        risk.danger=False;store=MemoryStore(card)
        class Uncertain(Telegram):
            def send_photo(self,*args):self.photos.append(args);raise TelegramSendError(uncertain=True)
        bot=Uncertain();service=OfflineCardService(store,bot,risk,None,None,None,lambda:Assets(),hash_salt='test')
        with patch('api.offline_card_service.render_offline_card',return_value=b'\x89PNG\r\n\x1a\nimage'):
            assert await service.deliver(card.card_id)=='uncertain'
            assert await service.deliver(card.card_id)=='uncertain'
        assert len(bot.photos)==1
    asyncio.run(run())


def test_invalid_model_choice_retries_once_then_uses_committed_fallback():
    async def run():
        calls=[]
        async def invalid(context):calls.append(context.card_id);raise ValueError('invalid choice')
        service=OfflineCardService(None,None,None,None,None,invalid,None,hash_salt='test')
        assert await service._choose(context())==__import__('api.offline_card',fromlist=['CardChoice']).CardChoice()
        assert len(calls)==2
    asyncio.run(run())


def test_watch_cards_enqueue_only_after_all_primary_messages_and_failure_does_not_repeat_text():
    from api.tests.test_dispatch import service,shop,request
    async def run():
        dispatch,store,bot,sinks=service([shop('one',chat=101),shop('two',chat=102)])
        class Cards:
            calls=[]
            async def enqueue_watch(self,event,target,recipient,alert_id):
                self.calls.append((recipient.telegram_chat_id,len(bot.messages),tuple(item.item_name for item in target.lift_first)))
                if len(self.calls)<=2:raise ValueError('optional queue unavailable before row')
        cards=Cards();dispatch.cards=cards
        result=await dispatch.process(request(level='watch'))
        assert result['status']=='pending' and len(bot.messages)==2
        assert len(cards.calls)==2 and all(count==2 for _,count,_ in cards.calls)
        assert all(items==('Synthetic stock',) for _,_,items in cards.calls)
        resumed=await dispatch.resume(result['event_id'])
        assert resumed['status']=='complete' and len(cards.calls)==4
        assert len(bot.messages)==2
    asyncio.run(run())


def test_public_card_handler_finishes_without_repeating_accepted_photo_or_sending_extra_text():
    from api.main import create_app
    from api.config import Settings
    from api.telegram_webhook import TelegramHandler
    from api.tests.test_telegram_webhook import request,HEADERS
    class Inbox:
        calls=[]
        def claim(self,*args):return 'claimed','owner'
        def transition(self,*args,**kwargs):self.calls.append((args,kwargs))
    class Cards:
        async def request_owner(self,chat,operation):
            assert chat==9 and len(operation)==64
            return 'accepted',None
    bot=Telegram();inbox=Inbox()
    handler=TelegramHandler(inbox,bot,cards=Cards())
    app=create_app(Settings(telegram_webhook_secret='test-secret'),handler=handler)
    payload={'update_id':5,'message':{'message_id':7,'date':1791856800,'chat':{'id':9,'type':'private'},'text':'/card'}}
    assert request(app,'POST','/telegram/webhook',headers=HEADERS,json=payload).status_code==200
    assert inbox.calls[-1][1]['outcome']=='card_accepted' and not bot.photos
    payload['message'].pop('date')
    assert request(app,'POST','/telegram/webhook',headers=HEADERS,json=payload).status_code==400

@pytest.mark.skipif(not os.getenv('FIRESTORE_EMULATOR_HOST'),reason='Firestore required')
def test_ordinary_synthetic_owner_card_real_risk_and_scenario_reset():
    from api.active_risk import ActiveRiskStore
    from api.demo_scenario import scenario_collection
    async def run():
        client=firestore.Client(project='highground-card-test',credentials=AnonymousCredentials())
        prefix='card_owner_'+uuid4().hex+'_'
        store=FirestoreCardStore(client,collection=prefix+'cards',shops=prefix+'shops')
        risk=ActiveRiskStore(client,risks=prefix+'risks',shops=store.shops,deliveries=prefix+'delivery',current_actions=prefix+'current',source_states=prefix+'sources',source_recoveries=prefix+'recoveries')
        shop=context().model_dump();shop.update(shop_id='ordinary-synthetic',shop_name='Synthetic owned shop',is_demo=True,recipients=[{'role':'owner','language':'en','telegram_chat_id':101}],baseline_inventory_id='inventory',lift_first=[{'item_name':'Rice','qty':2.,'value_rm':20.,'lift_effort':1}])
        class Reader:
            def shop_for_sender(self,chat):return shop if chat==101 else None
        class Destinations:
            def nearest(self,*args):return None
        bot=Telegram();service=OfflineCardService(store,bot,risk,Reader(),Destinations(),None,lambda:Assets(),hash_salt='test')
        scenario=client.collection(scenario_collection(store.shops)).document('current')
        try:
            client.collection(store.shops).document(shop['shop_id']).set({'is_demo':True},timeout=8,retry=None)
            scenario.set({'state':'ready','generation':7,'fixture_shop_ids':['demo-t16-1']},timeout=8,retry=None)
            with patch('api.offline_card_service.render_offline_card',return_value=b'\x89PNG\r\n\x1a\nimage'):
                assert (await service.request_owner(101,'message-operation'))[0]=='accepted'
                assert (await service.request_owner(101,'message-operation'))[0]=='accepted'
            assert len(bot.photos)==1
            record=next(client.collection(store.collection).stream(timeout=8,retry=None)).to_dict()
            assert record['context']['items'][0]['item_name']=='Rice'
            scenario.update({'generation':8},timeout=8,retry=None)
            assert not service._guard(__import__('api.offline_card',fromlist=['card_from_storage']).card_from_storage(record['context']),record['event'])
        finally:
            try:
                for name in (store.collection,store.shops,risk.risks,risk.deliveries,scenario_collection(store.shops)):
                    for doc in client.collection(name).stream(timeout=8,retry=None):doc.reference.delete(timeout=8,retry=None)
            finally:client.close()
    asyncio.run(run())
