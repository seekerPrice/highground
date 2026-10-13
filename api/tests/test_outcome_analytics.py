from types import SimpleNamespace
from copy import deepcopy
import pytest
from api.tests.test_outcomes import episode,respond,NOW
from api.outcome_store import episode_key
from api.outcome_analytics import OutcomeAnalytics
from api.tools.bigquery_queries import QueryRows

class Snapshot:
    def __init__(self,key,value):self.id,self.value=key,value
    def to_dict(self):return deepcopy(self.value)
class Collection:
    def __init__(self,rows):self.rows,self.bound=rows,None
    def limit(self,n):self.bound=n;return self
    def stream(self,**kwargs):assert kwargs=={'timeout':5,'retry':None};return iter(self.rows[:self.bound])
class FS:
    def __init__(self,rows):self.rows=rows
    def collection(self,key):return Collection(self.rows.get(key,[]))
class BQ:
    def __init__(self):self.inserted=[];self.closed=False
    def insert_rows_json(self,table,rows,**kwargs):self.inserted.append((table,rows,kwargs));return []
    def close(self):self.closed=True

def fixture(monkeypatch,*,cleanup='cleaned'):
    ep=episode();response=respond();key=episode_key(ep)
    fs=FS({'outcome_episodes':[Snapshot(key,{'json':ep.model_dump_json()})],'outcome_responses':[Snapshot(key,{'json':response.model_dump_json()})],'outcome_prompts':[Snapshot(key,{'status':'simulated','provenance':'synthetic_fixture'})]})
    bq=BQ();store=SimpleNamespace(client=fs,prefix='');service=OutcomeAnalytics(bq,'project','dataset',store,emulator_host='http://127.0.0.1:9050')
    rows=[service._fact(response,ep)];calls=[]
    def query(client,sql,**kwargs):calls.append((sql,kwargs));return QueryRows(tuple(deepcopy(rows)),cleanup)
    monkeypatch.setattr('api.outcome_analytics.query_rows',query)
    return service,fs,bq,rows,calls,ep,response

def test_identical_physical_duplicates_count_once_and_virtual_not_accepted(monkeypatch):
    service,fs,bq,rows,calls,ep,response=fixture(monkeypatch);rows.append(deepcopy(rows[0]))
    result=service.summary([{'shop_id':ep.shop_id,'is_demo':True}],2,NOW)
    assert result.status=='available' and result.coverage.responses==1 and result.coverage.fixture_prompts==1 and result.coverage.accepted_prompts==0
    assert result.coverage.missing_unknown==0
    assert all(private not in result.model_dump_json() for private in (ep.shop_id,ep.episode_id,response.owner_hash,response.response_id))
    config=calls[0][1]['job_config'];assert config.maximum_bytes_billed==100_000_000
    assert {p.name for p in config.query_parameters}=={'ids','shops','generation'}
    service.close();assert bq.closed

@pytest.mark.parametrize('failure',['conflict','missing','cleanup','overflow','real','generation'])
def test_incomplete_or_untrusted_scope_is_unavailable_not_zero(monkeypatch,failure):
    service,fs,bq,rows,calls,ep,response=fixture(monkeypatch,cleanup='failed' if failure=='cleanup' else 'cleaned')
    shops=[{'shop_id':ep.shop_id,'is_demo':True}];generation=2
    if failure=='conflict':rows.append({**rows[0],'outcome':'inside'})
    if failure=='missing':rows.clear()
    if failure=='overflow':fs.rows['outcome_episodes']*=1001
    if failure=='real':shops[0]['is_demo']=False
    if failure=='generation':generation=3;rows.clear()
    result=service.summary(shops,generation,NOW)
    if failure=='generation':assert result.status=='empty' and not result.coverage.responses
    else:assert result.status=='unavailable' and result.coverage is None and result.scenario_generation is None


def test_insert_preserves_observation_reference_whole_depth_and_no_owner_identity(monkeypatch):
    service,fs,bq,rows,calls,ep,response=fixture(monkeypatch)
    service.insert_outcome(response,ep);table,inserted,options=bq.inserted[0]
    assert table=='project.dataset.outcomes' and options=={'row_ids':[response.response_id],'retry':None,'timeout':5}
    assert inserted[0]['reference_at']==response.observed_at.isoformat() and inserted[0]['event_id'] is None
    assert 'owner_hash' not in inserted[0]
    with pytest.raises(ValueError):service.insert_outcome(response,episode(episode_id='other'))


def test_immutable_calibration_history_is_bounded_and_explicitly_seeded(monkeypatch):
    from api.tests.test_calibration import state,evidence
    from api.calibration import decide_calibration
    from datetime import timedelta
    service,fs,bq,rows,calls,ep,response=fixture(monkeypatch)
    batch=tuple(evidence(i).model_copy(update={'response':evidence(i).response.model_copy(update={'origin':'synthetic_fixture'})}) for i in range(5))
    decision=decide_calibration(state(),batch,now=NOW)
    current=state(version=decision.new_version,multiplier=decision.new_multiplier)
    fs.rows['outcome_calibration']=[Snapshot('state',{'json':current.model_dump_json()})]
    fs.rows['outcome_calibration_facts']=[Snapshot(f'fact-{i}',{'area':current.area,'is_demo':True,'scenario_generation':2,'evaluated_at':NOW,'json':decision.model_dump_json()}) for i in range(51)]
    summary=service.summary([{'shop_id':ep.shop_id,'is_demo':True}],2,NOW)
    assert summary.history_truncated and sum(len(a.history) for a in summary.calibration_areas)==50
    assert summary.calibration_areas[0].history[0].fixture_response_count==5
    fs.rows['outcome_calibration_facts'][0].value['evaluated_at']=NOW+timedelta(seconds=1)
    assert service.summary([{'shop_id':ep.shop_id,'is_demo':True}],2,NOW).status=='unavailable'


def test_incomplete_history_and_query_failure_do_not_claim_complete_zero(monkeypatch):
    service,fs,bq,rows,calls,ep,response=fixture(monkeypatch)
    key=episode_key(ep);fs.rows['outcome_episodes'][0].value['json']=ep.model_copy(update={'history_status':'incomplete'}).model_dump_json()
    assert service.summary([{'shop_id':ep.shop_id,'is_demo':True}],2,NOW).coverage is None
    fs.rows['outcome_episodes'][0].value['json']=ep.model_dump_json()
    def fail(*args,**kwargs):raise RuntimeError('PRIVATE SDK payload')
    monkeypatch.setattr('api.outcome_analytics.query_rows',fail)
    result=service.summary([{'shop_id':ep.shop_id,'is_demo':True}],2,NOW)
    assert result.status=='unavailable' and 'PRIVATE' not in result.model_dump_json()


def test_same_generation_unrelated_area_cannot_leak_into_public_history(monkeypatch):
    from api.tests.test_calibration import state,evidence
    from api.calibration import decide_calibration
    service,fs,bq,rows,calls,ep,response=fixture(monkeypatch)
    decision=decide_calibration(state(),tuple(evidence(i) for i in range(5)),now=NOW)
    unrelated=state(area='w2833t',version=1,multiplier=.9)
    fs.rows['outcome_calibration']=[Snapshot('private-area',{'json':unrelated.model_dump_json()})]
    fs.rows['outcome_calibration_facts']=[Snapshot('private-history',{'area':'w2833t','is_demo':True,'scenario_generation':2,'evaluated_at':NOW,'json':decision.model_dump_json()})]
    result=service.summary([{'shop_id':ep.shop_id,'is_demo':True}],2,NOW)
    assert result.status=='available' and result.calibration_areas==()
    assert 'w2833t' not in result.model_dump_json()
