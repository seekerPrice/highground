from copy import deepcopy
from types import SimpleNamespace
from datetime import timedelta
import pytest
from api.tests.test_outcome_store import Client,local_transactions
from api.tests.test_outcomes import NOW
from api.outcome_store import FirestoreOutcomeStore
from api.demo_scenario import SHOP_IDS,FIXTURE_ORIGIN
from infra.seed_outcomes import require_local,fixture_plan,OutcomeFixtureSeeder

ENV={'FIRESTORE_EMULATOR_HOST':'127.0.0.1:8787','PUBSUB_EMULATOR_HOST':'127.0.0.1:8797','STORAGE_EMULATOR_HOST':'http://127.0.0.1:4443','BIGQUERY_EMULATOR_HOST':'http://127.0.0.1:9050'}
class Analytics:
    def __init__(self):self.rows=[]
    def insert_outcome(self,response,episode):self.rows.append(response)
def setup():
    client=Client();store=FirestoreOutcomeStore(client,'salt');analytics=Analytics()
    client.rows['demo_scenario','current']={'state':'ready','generation':3,'fixture_shop_ids':list(SHOP_IDS)}
    for identity in SHOP_IDS:client.rows['shops',identity]={'shop_id':identity,'is_demo':True,'fixture_origin':FIXTURE_ORIGIN,'lat':3.0315,'lng':101.5356,'recipients':[]}
    return client,store,analytics,OutcomeFixtureSeeder(store,analytics)

def test_loopback_and_local_flags_are_required_before_factories(monkeypatch):
    from infra import seed_outcomes
    settings=SimpleNamespace(local_development=True,demo_mode=True,gcp_project='owned')
    for name in ENV:
        bad=dict(ENV);bad[name]='https://example.com:443' if name in ('STORAGE_EMULATOR_HOST','BIGQUERY_EMULATOR_HOST') else 'example.com:443'
        with pytest.raises(ValueError):require_local(settings,bad)
    require_local(settings,ENV)
    with pytest.raises(ValueError):require_local(SimpleNamespace(local_development=False,demo_mode=True,gcp_project='owned'),ENV)
    called=[];monkeypatch.setattr('api.tools.firestore.create_firestore_client',lambda *_:called.append('client'))
    monkeypatch.setattr(seed_outcomes,'load_settings',lambda:settings);monkeypatch.setattr('sys.argv',['seed_outcomes','--apply'])
    for name in ENV:monkeypatch.delenv(name,raising=False)
    with pytest.raises(ValueError):seed_outcomes.main()
    assert called==[]


def test_six_historical_scopes_shrink_then_grow_and_replay_is_immutable(local_transactions):
    client,store,analytics,seeder=setup();result=seeder.seed(now=NOW)
    assert result['multiplier']==.99 and result['version']==2 and result['synthetic_shops']==1 and result['historical_shop_episodes']==6
    first=deepcopy(client.rows);assert len(analytics.rows)==6
    assert seeder.seed(now=NOW+timedelta(hours=1))==result
    assert client.rows==first and len(analytics.rows)==6
    assert not any(name in ('alerts','events') for name,_ in client.rows)
    responses=[r for (name,_),r in client.rows.items() if name=='outcome_responses']
    assert len(responses)==6 and all('synthetic_fixture' in r['json'] for r in responses)
    assert all('telegram_chat_id' not in r for (name,_),r in client.rows.items() if name!='shops')

@pytest.mark.parametrize('kind',['reset','ordinary','missing'])
def test_unowned_scope_fails_before_any_write(local_transactions,kind):
    client,store,analytics,seeder=setup()
    if kind=='reset':client.rows['demo_scenario','current']['state']='resetting'
    if kind=='ordinary':client.rows['shops',SHOP_IDS[4]]['is_demo']=False
    if kind=='missing':del client.rows['shops',SHOP_IDS[5]]
    before=deepcopy(client.rows)
    with pytest.raises(ValueError):seeder.seed(now=NOW)
    assert client.rows==before and not analytics.rows
