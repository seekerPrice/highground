"""Public outcome service respects accepted transport, deferred Danger and history."""
import asyncio
from datetime import timedelta
from unittest.mock import Mock,patch
import pytest
from api.tests.test_outcomes import episode,NOW
from api.tests.test_outcome_store import Client,local_transactions
from api.outcome_store import FirestoreOutcomeStore
from api.outcome_service import OutcomeService
from api.tools.telegram import TelegramSendError


def service(local_transactions):
    client=Client();store=FirestoreOutcomeStore(client,'salt');ep=episode(closed_at=NOW);key=store.register_episode(ep)
    client.rows['shops','private-shop']={'shop_id':'private-shop','language':'en','lat':3.,'lng':101.,'is_demo':True,'recipients':[{'role':'owner','telegram_chat_id':101}]}
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    shops=Mock();shops.shop_for_sender.return_value=client.rows['shops','private-shop'];shops.danger_active.return_value=False
    risks=Mock();risks.claim_outcome_delivery.return_value=('claimed','lease')
    telegram=Mock();telegram.send_message.return_value=91
    svc=OutcomeService(store,Mock(),telegram,Mock(),risk_store=risks,shop_store=shops,clock=lambda:NOW)
    return svc,client,key


def test_prompt_acceptance_and_replay_do_not_resend(local_transactions):
    svc,client,key=service(local_transactions)
    with patch('api.outcome_service.text',side_effect=lambda lang,key,**kwargs:key):
        assert asyncio.run(svc._prompt(key))=='accepted'
        assert asyncio.run(svc._prompt(key))=='already_accepted'
    assert svc.telegram.send_message.call_count==1
    callbacks=svc.telegram.send_message.call_args.args[2]['inline_keyboard']
    assert all(len(button['callback_data'].encode())<=64 for row in callbacks for button in row)
    row=client.rows['outcome_prompts',key]
    assert row['message_id']==91 and row['status']=='accepted'


def test_final_danger_or_busy_shared_delivery_never_transports_and_remains_retryable(local_transactions):
    for status in ('active_danger','busy','superseded'):
        svc,client,key=service(local_transactions);svc.risks.claim_outcome_delivery.return_value=(status,None)
        assert asyncio.run(svc._prompt(key))==status
        assert not svc.telegram.send_message.called
        assert client.rows['outcome_prompts',key]['status']=='retryable'


def test_unknown_send_settles_uncertain_and_no_replay_transport(local_transactions):
    svc,client,key=service(local_transactions);svc.telegram.send_message.side_effect=TelegramSendError(uncertain=True)
    with patch('api.outcome_service.text',side_effect=lambda lang,key,**kwargs:key):
        assert asyncio.run(svc._prompt(key))=='uncertain'
        assert asyncio.run(svc._prompt(key))=='uncertain'
    assert svc.telegram.send_message.call_count==1


def test_prompted_answer_after_closure_records_reference_not_answer_time(local_transactions):
    svc,client,key=service(local_transactions)
    with patch('api.outcome_service.text',side_effect=lambda lang,key,**kwargs:key):asyncio.run(svc._prompt(key))
    row=client.rows['outcome_prompts',key];svc.clock=lambda:NOW+timedelta(hours=1)
    with patch('api.reply_guard.text',side_effect=lambda lang,key,**kwargs:key):reply=asyncio.run(svc.answer(101,row['callback_token'],91,'no'))
    from api.outcome_models import OwnerOutcome
    response=OwnerOutcome.model_validate_json(client.rows['outcome_responses',key]['json'])
    assert response.observed_at==NOW and response.answered_at==NOW+timedelta(hours=1)
    assert response.reference_basis=='episode_reference'
    assert 'outcome_recorded' in reply.text


def test_pretransport_guard_exception_is_retryable_not_uncertain(local_transactions):
    svc,client,key=service(local_transactions)
    svc.risks.claim_outcome_delivery.side_effect=RuntimeError('Risk read unavailable')
    with pytest.raises(RuntimeError):asyncio.run(svc._prompt(key))
    assert client.rows['outcome_prompts',key]['status']=='retryable'
    assert not svc.telegram.send_message.called


def test_simulation_and_unreviewed_notice_present_in_prompt(local_transactions):
    svc,client,key=service(local_transactions)
    svc.store.shop_for_sender.return_value['language']='ms'
    with patch('api.outcome_service.text',side_effect=lambda lang,key,**kwargs:key):asyncio.run(svc._prompt(key))
    sent=svc.telegram.send_message.call_args.args[1]
    assert sent.startswith('simulation_label\n') and sent.endswith('\ntranslation_notice')


def test_manual_job_replay_counts_only_new_transport_acceptance(local_transactions):
    svc,client,key=service(local_transactions)
    svc.history.refresh.return_value=(key,)
    svc.history.calibration_batches.return_value=({},())
    svc.outcomes.pending=Mock(return_value=())
    svc._pending_facts=Mock(return_value=())
    first=asyncio.run(svc.ask(1));second=asyncio.run(svc.ask(1))
    assert first['prompts_accepted']==1 and second['prompts_accepted']==0
    assert svc.telegram.send_message.call_count==1


def test_escalation_after_prepare_and_render_prevents_actual_transport(local_transactions):
    svc,client,key=service(local_transactions)
    svc.risks.claim_outcome_delivery.side_effect=[('claimed','lease'),('active_danger',None)]
    assert asyncio.run(svc._prompt(key))=='active_danger'
    assert not svc.telegram.send_message.called and client.rows['outcome_prompts',key]['status']=='retryable'


def test_elapsed_job_retains_inflight_but_observes_eventual_exception(local_transactions):
    from threading import Event
    svc,client,key=service(local_transactions);svc.max_job_seconds=.01
    release=Event()
    def blocked(**kwargs):
        release.wait(1)
        raise TimeoutError('Elapsed bounded read')
    svc.history.refresh.side_effect=blocked
    svc.outcomes.pending=Mock(return_value=())
    async def run():
        observed=[];asyncio.get_running_loop().set_exception_handler(lambda loop,context:observed.append(context))
        result=await svc.ask(1)
        assert result=={'status':'deadline_limited','inflight_unknown':1}
        release.set()
        await asyncio.sleep(.03)
        assert svc.running.done() and not observed and not svc.outcomes.pending.called
        await svc.close()
    asyncio.run(run())


@pytest.mark.parametrize('closed',[True,False])
def test_owner_prompt_identifies_confirmed_interval_without_claiming_water_time(local_transactions,closed):
    svc,client,key=service(local_transactions)
    ep=svc.outcomes.episode(key)
    if not closed:
        ep=ep.model_copy(update={'closed_at':None})
        client.rows['outcome_episodes',key]['json']=ep.model_dump_json()
        client.rows['active_risks',ep.shop_id]={'episode_id':ep.episode_id}
    assert asyncio.run(svc._prompt(key))=='accepted'
    sent=svc.telegram.send_message.call_args.args[1]
    assert 'Episode reference (UTC)' in sent and ep.started_at.isoformat() in sent
    if closed:
        assert ep.closed_at.isoformat() in sent and 'not owner-observed water times' in sent
    else:assert 'No closure recorded' in sent and 'does not establish current flooding' in sent
    assert sent.startswith('SIMULATION') and len(sent)<=4096
