"""Bounded service semantics through atomic store doubles; no live SDK/model."""
import asyncio
from datetime import timedelta
from unittest.mock import patch
from api.public_check_service import PublicCheckService
from api.public_check_models import CheckLocation
from api.public_check_store import FirestoreCheckIntentStore
from api.agents.public_check import SummaryChoice
from api.tests.test_public_check import NOW,LOCATION,source,warning,report,project_check
from api.tests.test_public_check_intents import Client,transactional

class Shops:
    def __init__(self):self.danger=False;self.registered=False;self.writes=[]
    def shop_for_sender(self,sender):return dict(shop_id='PRIVATE-SHOP',language='en',lat=3.,lng=101.,is_demo=False) if self.registered else None
    def danger_active(self,identity):return self.danger
class Reader:
    def __init__(self,result=None):self.calls=0;self.result=result or project_check(LOCATION,(source(warning()),),(),(),now=NOW);self.gate=None
    async def read(self,location):
        self.calls+=1
        if self.gate:await self.gate.wait()
        return self.result
class Summary:
    def __init__(self):self.calls=0;self.bad=False
    async def summarize(self,result,**kwargs):
        self.calls+=1
        return SummaryChoice('check_summary_no_mapped' if self.bad else 'check_summary_warning','model')
    async def close(self):pass

def service(*,budget=25,result=None):
    client=Client();intents=FirestoreCheckIntentStore(client,'private-salt');shops=Shops();reader=Reader(result);summary=Summary()
    active=PublicCheckService(shops,intents,reader,summary,clock=lambda:NOW,total_budget_seconds=budget)
    return active,client,shops,reader,summary


def test_public_lookup_never_registers_or_persists_submitted_point_replay_skips_model():
    async def run():
        active,client,shops,reader,summary=service()
        start=await active.start(123,'start')
        context,bound=await active.context(123,'location-operation');assert not bound
        point=CheckLocation(lat=12.3456789,lng=98.7654321)
        summary.bad=True
        reply=await active.lookup(123,'location-operation',point,context)
        assert 'reports Warning' in reply.text and 'No fresh mapped observation' not in reply.text
        context,bound=await active.context(123,'location-operation');assert bound
        replay=await active.lookup(123,'location-operation',CheckLocation(lat=0.,lng=0.),context)
        assert replay.text==reply.text and reader.calls==summary.calls==1
        assert not shops.writes
        private=str(client.data)
        for value in ('12.3456789','98.7654321','PRIVATE-SHOP',"'lat'","'lng'","'latitude'"):
            assert value not in private
        new_context,new_bound=await active.context(123,'different-new-location')
        assert new_context is None and not new_bound
        await active.close()
    with patch('api.public_check_store.firestore.transactional',transactional):asyncio.run(run())


def test_registered_danger_bypasses_intent_open_reader_and_model():
    async def run():
        active,client,shops,reader,summary=service();shops.registered=True;shops.danger=True
        reply=await active.start(123,'start')
        assert reply.kind=='danger' and not client.data and reader.calls==summary.calls==0
        assert not reply.reply_markup or not any('request_location' in button for row in reply.reply_markup.get('keyboard',[]) for button in row)
        await active.close()
    with patch('api.public_check_store.firestore.transactional',transactional):asyncio.run(run())


def test_timeout_retains_readonly_work_and_releases_retryable_claim_without_false_cancel():
    async def run():
        active,client,shops,reader,summary=service(budget=.03)
        reader.gate=asyncio.Event()
        await active.start(123,'start');context,_=await active.context(123,'location')
        reply=await active.lookup(123,'location',LOCATION,context)
        assert 'unavailable right now' in reply.text and summary.calls==0
        assert active.pending, 'Timeout does not claim an underlying reader was cancelled'
        reader.gate.set();await asyncio.gather(*tuple(active.pending));await asyncio.sleep(0)
        record=next(row for (collection,_),row in client.data.items() if collection==active.intents.intents)
        assert record['status']=='retryable'
        context,_=await active.context(123,'location')
        reply=await active.lookup(123,'location',LOCATION,context)
        assert 'reports Warning' in reply.text
        await active.close()
    with patch('api.public_check_store.firestore.transactional',transactional):asyncio.run(run())


def test_stale_request_final_send_and_competing_location_flow_remove_gps_prompt():
    async def run():
        active,client,*_=service();reply=await active.start(123,'start')
        waiting=await active.recheck_reply(123,reply,registered_flow_waiting=True)
        assert 'Finish the pending' in waiting.text and waiting.reply_markup=={'remove_keyboard':True}
        active.clock=lambda:NOW+timedelta(minutes=5)
        expired=await active.recheck_reply(123,reply)
        assert 'expired or finished' in expired.text and expired.reply_markup=={'remove_keyboard':True}
        await active.close()
    with patch('api.public_check_store.firestore.transactional',transactional):asyncio.run(run())


def test_registered_danger_arriving_during_reader_bypasses_optional_generation():
    async def run():
        active,client,shops,reader,summary=service();shops.registered=True
        await active.start(123,'start');context,_=await active.context(123,'location')
        original=reader.read
        async def read(point):
            result=await original(point);shops.danger=True;return result
        reader.read=read
        reply=await active.lookup(123,'location',LOCATION,context)
        assert reply.kind=='danger' and summary.calls==0
        record=next(row for (collection,_),row in client.data.items() if collection==active.intents.intents)
        assert record['status']=='retryable'
        await active.close()
    with patch('api.public_check_store.firestore.transactional',transactional):asyncio.run(run())


def localized_boundaries():
    import json
    from pathlib import Path
    source=json.loads(Path('api/i18n/en.json').read_text())
    def render(language,key,**values):
        assert language=='ms'
        return 'UNREVIEWED-TRANSLATION-NOTICE' if key=='translation_notice' else source[key].format(**values)
    return render


def test_nonenglish_exception_and_overflow_keep_notice_and_qualifications():
    async def run():
        active,*_=service()
        start=await active.start(123,'start',language_hint='ms');context,_=await active.context(123,'location')
        async def fail(point):raise OSError('Source unavailable')
        active.reader.read=fail
        failed=await active.lookup(123,'location',LOCATION,context)
        assert 'UNREVIEWED-TRANSLATION-NOTICE' in failed.text
        assert 'does not mean there is no flood' in failed.text
        result=project_check(LOCATION,(source(*(warning(source_id=str(i)) for i in range(5))),),(),(),now=NOW)
        basic=localized_boundaries()
        def long(language,key,**values):return 'bounded translated observation '*100 if key=='check_observation' else basic(language,key,**values)
        with patch('api.public_check_service.text',long):
            overflow=active.render(result,'ms','a'*64)
        assert len(overflow.text)<=4096
        assert 'UNREVIEWED-TRANSLATION-NOTICE' in overflow.text
        assert 'not authenticate' in overflow.text and 'Current opening, accessibility and safety are unknown' in overflow.text
        assert 'reports Warning' in overflow.text
        await active.close()
    with patch('api.public_check_store.firestore.transactional',transactional),patch('api.public_check_service.catalog',lambda language:{'_reviewed':False}),patch('api.public_check_service.text',localized_boundaries()):asyncio.run(run())


def test_long_public_destination_caption_bounded_with_full_sourced_name_and_caution():
    import json
    from pathlib import Path
    from api.destinations import SafePoint
    point=SafePoint.model_validate(json.loads(Path('infra/data/safe_points.json').read_text())[0]).model_copy(update={'name':'A'*100})
    result=project_check(LOCATION,(),(),(point,),now=NOW)
    active,*_=service();reply=active.render(result,'en','a'*64)
    assert 'A'*100 in reply.text and point.source_date in reply.text
    assert len(reply.reply_markup['inline_keyboard'][0][0]['text'])<=64
    assert 'Current opening, accessibility and safety are unknown' in reply.text
