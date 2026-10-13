"""Transactions exercised without SDK/network calls; real persistence is separate."""
from copy import deepcopy
from datetime import timedelta
import pytest
from api.tests.test_outcomes import episode,NOW

class Snapshot:
    def __init__(self,value):self.value=deepcopy(value)
    def to_dict(self):return self.value
class Ref:
    def __init__(self,client,path):self.client,self.path=client,path
    def get(self,**kwargs):return Snapshot(self.client.rows.get(self.path))
class Collection:
    def __init__(self,client,name):self.client,self.name=client,name
    def document(self,key):return Ref(self.client,(self.name,key))
class Transaction:
    def __init__(self,client):self.client,self.pending=client,[]
    def create(self,ref,value):
        if ref.path in self.client.rows:raise ValueError('Already exists')
        self.pending.append((ref.path,deepcopy(value)))
    def set(self,ref,value):self.pending.append((ref.path,deepcopy(value)))
class Client:
    def __init__(self):self.rows={}
    def collection(self,name):return Collection(self,name)
    def transaction(self,**kwargs):return Transaction(self)
@pytest.fixture
def local_transactions(monkeypatch):
    def decorator(fn):
        def run(tx):
            result=fn(tx)
            for key,value in tx.pending:tx.client.rows[key]=value
            return result
        return run
    monkeypatch.setattr('google.cloud.firestore.transactional',decorator)


def test_episode_roundtrip_preserves_tuple_timestamps_and_conflicting_start_rejected(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    client=Client();store=FirestoreOutcomeStore(client,'salt')
    first=episode();key=store.register_episode(first)
    assert store.episode(key)==first
    with pytest.raises(ValueError):store.register_episode(first.model_copy(update={'started_at':NOW-timedelta(hours=8)}))
    assert store.episode(key)==first


def test_untrusted_actor_cannot_create_response_or_analytics_fact(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    client=Client();store=FirestoreOutcomeStore(client,'salt');key=store.register_episode(episode())
    client.rows['shops','private-shop']={'is_demo':True,'recipients':[{'role':'owner','telegram_chat_id':101}]}
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    before=deepcopy(client.rows)
    with pytest.raises(ValueError):store.record_response(key,sender_chat_id=202,answer='no',observed_at=NOW,now=NOW)
    assert client.rows==before


def test_calibration_cas_consumes_canonical_scopes_atomically_and_retry_is_noop(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    from api.tests.test_calibration import evidence,state
    client=Client();store=FirestoreOutcomeStore(client,'salt');batch=tuple(evidence(i) for i in range(5))
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    from api.outcome_store import episode_key
    for row in batch:
        store.register_episode(row.episode)
        client.rows['outcome_responses',episode_key(row.episode)]={'json':row.response.model_dump_json()}
    changed=store.calibrate(state(),batch,now=NOW)
    assert changed.new_multiplier==.9
    with pytest.raises(ValueError):store.calibrate(state(),batch,now=NOW)
    current=state(version=1,multiplier=.9)
    assert store.calibrate(current,batch,now=NOW).reason=='no_fresh_evidence'
    assert len([key for key in client.rows if key[0]=='outcome_consumed'])==5


def test_current_owner_first_response_and_fact_are_atomic_and_immutable(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    client=Client();store=FirestoreOutcomeStore(client,'salt');key=store.register_episode(episode())
    client.rows['shops','private-shop']={'is_demo':True,'recipients':[{'role':'owner','telegram_chat_id':101}]}
    client.rows['active_risks','private-shop']={'episode_id':'confirmed-episode'}
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    first=store.record_response(key,sender_chat_id=101,answer='no',observed_at=NOW,now=NOW)
    assert store.record_response(key,sender_chat_id=101,answer='inside',observed_at=NOW,now=NOW)==first
    assert client.rows['outcome_facts',key]['json']==first.model_dump_json()
    client.rows['active_risks','private-shop']['legacy_unknown']=True
    with pytest.raises(ValueError):store.record_response(key,sender_chat_id=101,answer='inside',observed_at=NOW,now=NOW)


def test_calibration_rejects_unpersisted_evidence_and_old_generation_without_consumption(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    from api.tests.test_calibration import evidence,state
    client=Client();store=FirestoreOutcomeStore(client,'salt');batch=tuple(evidence(i) for i in range(5))
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    before=deepcopy(client.rows)
    with pytest.raises(ValueError):store.calibrate(state(),batch,now=NOW)
    assert client.rows==before
    client.rows['demo_scenario','current']['generation']=3
    before=deepcopy(client.rows)
    with pytest.raises(ValueError):store.calibrate(state(),batch,now=NOW)
    assert client.rows==before


def test_prompt_final_danger_guard_and_expired_send_are_not_automatically_retried(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    client=Client();store=FirestoreOutcomeStore(client,'salt');key=store.register_episode(episode())
    client.rows['shops','private-shop']={'is_demo':True,'recipients':[{'role':'owner','telegram_chat_id':101}]}
    client.rows['active_risks','private-shop']={'episode_id':'confirmed-episode'}
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    claimed=store.claim_prompt(key,now=NOW);assert claimed['status']=='preparing'
    client.rows['active_risks','private-shop']['legacy_unknown']=True
    assert store.mark_prompt_sending(key,claimed['owner'],now=NOW)['status']=='active_danger'
    client.rows['active_risks','private-shop']['legacy_unknown']=False
    claimed=store.claim_prompt(key,now=NOW)
    assert store.mark_prompt_sending(key,claimed['owner'],now=NOW)['status']=='sending'
    assert store.claim_prompt(key,now=NOW+timedelta(seconds=31))['status']=='uncertain'
    assert store.claim_prompt(key,now=NOW+timedelta(days=1))['status']=='uncertain'


def test_accepted_prompt_retry_never_creates_a_second_send(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    client=Client();store=FirestoreOutcomeStore(client,'salt');key=store.register_episode(episode())
    client.rows['shops','private-shop']={'is_demo':True,'recipients':[{'role':'owner','telegram_chat_id':101}]}
    client.rows['active_risks','private-shop']={'episode_id':'confirmed-episode'}
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    claimed=store.claim_prompt(key,now=NOW);store.mark_prompt_sending(key,claimed['owner'],now=NOW)
    store.finish_prompt(key,claimed['owner'],now=NOW,status='accepted',message_id=42)
    assert store.claim_prompt(key,now=NOW+timedelta(hours=1))['status']=='accepted'
    with pytest.raises(ValueError):store.finish_prompt(key,claimed['owner'],now=NOW,status='retryable')


def test_callback_opaque_mapping_is_owner_bound_small_and_stable(local_transactions):
    from api.outcome_store import FirestoreOutcomeStore
    client=Client();store=FirestoreOutcomeStore(client,'salt');key=store.register_episode(episode())
    client.rows['shops','private-shop']={'is_demo':True,'recipients':[{'role':'owner','telegram_chat_id':101}]}
    client.rows['active_risks','private-shop']={'episode_id':'confirmed-episode'}
    client.rows['demo_scenario','current']={'state':'ready','generation':2}
    first=store.claim_prompt(key,now=NOW);token=first['callback_token']
    assert len(f'outcome:{token}:entrance'.encode())<=64 and token!=key[:32]
    with pytest.raises(ValueError):store.resolve_prompt_token(token,sender_chat_id=101,message_id=42,now=NOW)
    retry=store.claim_prompt(key,now=NOW+timedelta(seconds=61))
    assert retry['callback_token']==token
    store.mark_prompt_sending(key,retry['owner'],now=NOW+timedelta(seconds=61))
    store.finish_prompt(key,retry['owner'],now=NOW+timedelta(seconds=61),status='accepted',message_id=42)
    assert store.resolve_prompt_token(token,sender_chat_id=101,message_id=42,now=NOW+timedelta(seconds=62))==key
    with pytest.raises(ValueError):store.resolve_prompt_token(token,sender_chat_id=202,message_id=42,now=NOW)
    client.rows['demo_scenario','current']['generation']=3
    with pytest.raises(ValueError):store.resolve_prompt_token(token,sender_chat_id=101,message_id=42,now=NOW)
