import asyncio
from datetime import datetime,UTC
from hashlib import sha256
from uuid import uuid4
import os
import pytest
from api.tools.firestore import create_firestore_client
from api.config import Settings
from api.stock_confirmations import StockActionStore,StockConfirmationService
from api.dispatch_models import Shop,ActionSnapshot,LiftItem
from api.agents.sessions import session_user_id
from api.tests.test_vehicle_confirmations import Sink
from api.tests.test_dispatch_emulators import _cleanup_scope
from api.tools.bigquery_queries import query_rows

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_exact_displayed_snapshot_cross_recipient_refresh_episode_and_outbox():
    client=create_firestore_client(Settings(gcp_project='highground-task11-tests'));prefix='stock-'+uuid4().hex
    store=StockActionStore(client,actions=prefix+'a',confirmations=prefix+'f',alerts=prefix+'l',shops=prefix+'s',risks=prefix+'r')
    shop=Shop(shop_id='shop',shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,
        recipients=[dict(telegram_chat_id=101,language='en',role='owner'),dict(telegram_chat_id=102,language='en',role='worker')])
    shop_ref=client.collection(store.shops).document('shop');shop_ref.set(shop.model_dump())
    from api.active_risk import ActiveRiskStore
    risk=ActiveRiskStore(client,risks=store.risks,shops=store.shops)
    event=dict(event_id='event',source='demo',level='warning',created_at=datetime.now(UTC),is_demo=True)
    event['episode_id']=risk.apply_event(event,shop.shop_id)
    snapshot=ActionSnapshot(inventory_id='old',items=(LiftItem(item_name='Rice',qty=2.,value_rm=20.,lift_effort=1),),estimated_value_rm=20.)
    action=store.prepare(event,shop,snapshot,'salt');identity=action['action_id']
    for member in shop.recipients:
        sender_hash=session_user_id(member.telegram_chat_id,'salt')
        alert_id=sha256(f"event:shop:{sender_hash}".encode()).hexdigest()
        client.collection(store.alerts).document(alert_id).set(dict(status='accepted',message_id=member.telegram_chat_id+1000,level='warning',snapshot=action['snapshot']))
    sink=Sink();service=StockConfirmationService(store,sink,hash_salt='salt')
    async def run():
        assert (await service.record(identity,sender_chat_id=999,message_chat_id=999,message_id=1101))[0]=='unavailable'
        assert (await service.record(identity,sender_chat_id=101,message_chat_id=101,message_id=999))[0]=='unavailable'
        # Later refresh cannot revalue an older accepted immutable alert.
        shop_ref.update(dict(baseline_inventory_id='new',lift_first_value_rm=999.))
        results=await asyncio.gather(service.record(identity,sender_chat_id=101,message_chat_id=101,message_id=1101),
                                    service.record(identity,sender_chat_id=102,message_chat_id=102,message_id=1102))
        assert sorted(r[0] for r in results)==['already_recorded','recorded']
        saved=client.collection(store.confirmations).document(identity).get().to_dict()
        assert saved['protected_value_rm']==20 and saved['snapshot']['inventory_id']=='old'
        await service.flush(identity);assert not sink.rows
        sink.fail=False;await service.flush(identity);await service.flush(identity)
        assert len(sink.rows)==1 and sink.rows[0]['episode_id']==event['episode_id']
        risk.apply_event(dict(event_id='danger',source='demo',level='danger',created_at=datetime.now(UTC),is_demo=True),shop.shop_id)
        assert (await service.record(identity,sender_chat_id=101,message_chat_id=101,message_id=1101))[0]=='superseded'
    try:asyncio.run(run())
    finally:
        for collection in (store.actions,store.confirmations,store.alerts,store.shops,store.risks):
            for doc in client.collection(collection).stream():doc.reference.delete()
        client.close()

@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_actual_warning_to_private_stock_done_callback_freezes_inventory():
    import httpx,json
    from api.dispatch import DispatchService
    from api.dispatch_models import EventRequest
    from api.dispatch_store import FirestoreDispatchStore
    from api.active_risk import ActiveRiskStore
    from api.telegram_webhook import TelegramHandler
    from api.telegram_inbox import FirestoreInbox
    from api.main import create_app
    from api.tests.test_dispatch import Sinks
    from api.tests.test_telegram_webhook import request
    from api.tools.telegram import TelegramAPI
    client=create_firestore_client(Settings(gcp_project='highground-task11-tests'));prefix='stock-dispatch-'+uuid4().hex
    dispatch_store=FirestoreDispatchStore(client,events=prefix+'e',alerts=prefix+'a',shops=prefix+'s')
    stocks=StockActionStore(client,actions=prefix+'stock',confirmations=prefix+'f',alerts=dispatch_store.alerts,shops=dispatch_store.shops,risks=prefix+'risk')
    risk=ActiveRiskStore(client,risks=prefix+'risk',shops=dispatch_store.shops,deliveries=prefix+'delivery',current_actions=prefix+'current')
    shop=Shop(shop_id='shop',shop_name='Synthetic',lat=3.,lng=101.,is_demo=True,baseline_inventory_id='old',
        lift_first=[LiftItem(item_name='Rice',qty=2.,value_rm=20.,lift_effort=1)],
        recipients=[dict(telegram_chat_id=101,language='en',role='owner')])
    client.collection(dispatch_store.shops).document('shop').set(shop.model_dump())
    calls=[]
    def transport(req):
        calls.append((req.url.path.rsplit('/',1)[1],json.loads(req.content)))
        return httpx.Response(200,json=dict(ok=True,result=dict(message_id=77)))
    bot=TelegramAPI('synthetic',httpx.MockTransport(transport));sinks=Sinks();sinks.fail=False
    service=DispatchService(dispatch_store,bot,sinks,hash_salt='salt',stock_actions=stocks,active_risk=risk)
    confirm_sink=Sink();confirm_sink.fail=False;confirm=StockConfirmationService(stocks,confirm_sink,hash_salt='salt')
    inbox=FirestoreInbox(client,prefix+'inbox');handler=TelegramHandler(inbox,bot,stock_confirmations=confirm)
    app=create_app(Settings(telegram_webhook_secret='synthetic-secret'),handler)
    try:
        result=asyncio.run(service.process(EventRequest(request_id='warning',level='warning',lat=3.,lng=101.,warning_structure='warning_intro_fallback')))
        alert=dispatch_store.get_alert(dispatch_store.get_event(result['event_id'])['alert_ids'][0])
        snapshot=ActionSnapshot.model_validate(alert['snapshot']);assert snapshot.estimated_value_rm==20
        assert any(b['callback_data']=='stock:'+snapshot.stock_action_id for row in alert['reply_markup']['inline_keyboard'] for b in row if 'callback_data' in b)
        assert '≈RM20.00' in alert['text'] and 'Quick 30-second' in alert['text']
        client.collection(dispatch_store.shops).document('shop').update(dict(baseline_inventory_id='fresh',lift_first_value_rm=999.))
        payload=dict(update_id=501,callback_query=dict(id='callback',**{'from':dict(id=101)},message=dict(message_id=77,date=int(datetime.now(UTC).timestamp()),chat=dict(id=101,type='private')),data='stock:'+snapshot.stock_action_id))
        response=request(app,'POST','/telegram/webhook',headers={'X-Telegram-Bot-Api-Secret-Token':'synthetic-secret'},json=payload)
        assert response.status_code==200 and confirm_sink.rows[0]['protected_value_rm']==20
        assert confirm_sink.rows[0]['episode_id']==risk.get('shop').episode_id
    finally:
        for name in (dispatch_store.events,dispatch_store.alerts,dispatch_store.shops,dispatch_store.plans,dispatch_store.deliveries,stocks.actions,stocks.confirmations,stocks.risks,risk.deliveries,risk.current_actions,inbox.collection):
            for doc in client.collection(name).stream():doc.reference.delete()
        client.close()

@pytest.mark.skipif(not all(os.environ.get(name) for name in ('BIGQUERY_EMULATOR_HOST','PUBSUB_EMULATOR_HOST')),reason='local analytics emulators required')
def test_official_stock_rows_and_conservative_demo_episode_aggregate():
    import json
    from pathlib import Path
    from google.cloud import bigquery
    from api.config import load_settings
    from api.tools.cloud_events import create_event_sinks
    from api.stock_confirmations import estimated_lifted_value_sql
    settings=load_settings();dataset='stock_test_'+uuid4().hex
    with _cleanup_scope() as cleanup:
        sinks=create_event_sinks(Settings(gcp_project=settings.gcp_project,bigquery_dataset=dataset));cleanup.extend([sinks.analytics.close,sinks.publisher.stop])
        full=f'{settings.gcp_project}.{dataset}'
        cleanup.append(lambda:sinks.analytics.delete_dataset(full,delete_contents=True,not_found_ok=True,timeout=25,retry=None))
        sinks.analytics.create_dataset(bigquery.Dataset(full),timeout=8,retry=None)
        schema=json.loads((Path(__file__).parents[2]/'infra/schemas/confirmations.json').read_text())
        sinks.analytics.create_table(bigquery.Table(full+'.confirmations',schema=[bigquery.SchemaField.from_api_repr(f) for f in schema]),timeout=8,retry=None)
        rows=[('a','shop','episode',20,True),('b','shop','episode',100,True),
              ('c','shop','new-episode',30,True),('d','other','episode',20,True),('real','private','episode',999,False)]
        for identity,shop,episode,value,demo in rows:
            record=dict(confirmation_id=identity,action_id=identity,episode_id=episode,alert_id=identity,
                event_id=identity,shop_id=shop,kind='stock',protected_value_rm=value,is_demo=demo,confirmed_at=datetime.now(UTC))
            sinks.insert_confirmation(record)
            if identity=='b':sinks.insert_confirmation(record)
        query=query_rows(sinks.analytics,estimated_lifted_value_sql(settings.gcp_project,dataset),project=settings.gcp_project,emulator_endpoint=os.environ['BIGQUERY_EMULATOR_HOST'],timeout=8);assert query.cleanup=='cleaned';result=query.rows
        assert float(result[0].estimated_stock_value_reported_lifted)==150


def test_stock_callback_feedback_fits_telegram_limit_in_all_languages():
    from api.i18n import LANGUAGES,catalog,text
    for language in LANGUAGES:
        for key in ('stock_recorded','stock_already_recorded','confirmation_superseded','confirmation_unavailable'):
            notice='' if catalog(language)['_reviewed'] else '\n'+text(language,'translation_notice')
            assert len(text(language,key)+notice)<=200

@pytest.mark.parametrize('recovery',['demo_reset','photo_recovery','official_recovery'])
@pytest.mark.skipif(not os.environ.get('FIRESTORE_EMULATOR_HOST'),reason='Firestore emulator required')
def test_closed_episode_old_stock_callback_rejected_new_episode_works(recovery):
    from api.active_risk import ActiveRiskStore
    client=create_firestore_client(Settings(gcp_project='highground-task11-tests'));prefix='closed-stock-'+uuid4().hex
    stocks=StockActionStore(client,actions=prefix+'a',confirmations=prefix+'f',alerts=prefix+'l',shops=prefix+'s',risks=prefix+'r')
    risk=ActiveRiskStore(client,risks=stocks.risks,shops=stocks.shops,current_actions=prefix+'v',source_states=prefix+'sources')
    demo=recovery=='demo_reset'
    shop=Shop(shop_id='shop',shop_name='Synthetic',lat=3.,lng=101.,is_demo=demo,
        recipients=[dict(telegram_chat_id=101,language='en',role='owner')])
    client.collection(stocks.shops).document('shop').set(shop.model_dump())
    snapshot=ActionSnapshot(inventory_id='inventory',items=(LiftItem(item_name='Rice',qty=2.,value_rm=20.,lift_effort=1),),estimated_value_rm=20.)
    source='demo' if demo else ('jps' if recovery=='official_recovery' else 'shop_report')
    def event(identity,level):
        now=datetime.now(UTC)
        return dict(event_id=identity,source=source,level=level,is_demo=demo,created_at=now,
                    source_key='station' if source=='jps' else None,source_episode_id='source-episode',source_observed_at=now)
    def prepare(value):
        episode=risk.apply_event(value,'shop');assert episode
        value['episode_id']=episode
        action=stocks.prepare(value,shop,snapshot,'salt')
        sender_hash=session_user_id(101,'salt')
        alert_id=sha256(f"{value['event_id']}:shop:{sender_hash}".encode()).hexdigest()
        client.collection(stocks.alerts).document(alert_id).set(dict(status='accepted',message_id=77,level='warning',snapshot=action['snapshot']))
        return action
    try:
        old=prepare(event('old-warning','warning'))
        if not demo:risk.apply_event(event('danger','danger'),'shop')
        if demo:assert risk.reset_demo('shop')
        elif recovery=='photo_recovery':assert risk.owner_declared_recovery('shop',101)
        else:assert risk.recover_official('station','source-episode',datetime.now(UTC))==1
        assert risk.get('shop').episode_id is None
        late=event('late-warning','warning');late['episode_id']=old['episode_id']
        assert stocks.prepare(late,shop,snapshot,'salt')['state']=='superseded'
        service=StockConfirmationService(stocks,Sink(),hash_salt='salt')
        result=asyncio.run(service.record(old['action_id'],sender_chat_id=101,message_chat_id=101,message_id=77))
        assert result[0]=='superseded'
        assert not list(client.collection(stocks.confirmations).stream())
        new=prepare(event('new-warning','warning'))
        assert new['episode_id']!=old['episode_id']
        assert asyncio.run(service.record(new['action_id'],sender_chat_id=101,message_chat_id=101,message_id=77))[0]=='recorded'
    finally:
        for name in (stocks.actions,stocks.confirmations,stocks.alerts,stocks.shops,stocks.risks,risk.current_actions,risk.source_states):
            for doc in client.collection(name).stream():doc.reference.delete()
        client.close()
