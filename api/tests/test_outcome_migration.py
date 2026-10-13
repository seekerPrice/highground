from types import SimpleNamespace
import pytest
from google.cloud import bigquery
from infra.migrate_outcomes import migrate
from api.tools.bigquery_queries import QueryRows
import json
from pathlib import Path
FIELDS=tuple(bigquery.SchemaField.from_api_repr(v) for v in json.loads(Path('infra/schemas/outcomes.json').read_text()))
class Client:
    def __init__(self,count=8):self.project='owned';self._connection=SimpleNamespace(API_BASE_URL='http://127.0.0.1:9050');self.table=SimpleNamespace(project='owned',dataset_id='local',table_id='outcomes',schema=list(FIELDS[:count]));self.updates=[]
    def get_table(self,identity,**kwargs):assert identity=='owned.local.outcomes';assert kwargs=={'retry':None,'timeout':5};return self.table
    def update_table(self,table,fields,**kwargs):self.updates.append((fields,kwargs));return table

def test_original_schema_only_adds_nullable_fields_then_requires_actual_select(monkeypatch):
    client=Client();calls=[]
    def query(client,sql,**kwargs):calls.append((sql,kwargs));return QueryRows((),'cleaned')
    monkeypatch.setattr('infra.migrate_outcomes.query_rows',query)
    result=migrate(client,'owned','local',emulator_host='http://127.0.0.1:9050',apply=True)
    assert result=='verified' and client.updates==[(['schema'],{'retry':None,'timeout':5})]
    assert len(client.table.schema)==16 and all(s.mode=='NULLABLE' for s in client.table.schema)
    assert all(name in calls[0][0] for name in ('episode_id','area','reference_basis','reference_at','answered_at','entrypoint','origin','scenario_generation'))

def test_dryrun_does_not_update_or_query_and_new_schema_is_idempotent(monkeypatch):
    client=Client();monkeypatch.setattr('infra.migrate_outcomes.query_rows',lambda *a,**k:pytest.fail('Dry run queried'))
    assert migrate(client,'owned','local',emulator_host='http://127.0.0.1:9050')=='pending' and not client.updates
    client=Client(16);monkeypatch.setattr('infra.migrate_outcomes.query_rows',lambda *a,**k:QueryRows((),'cleaned'))
    assert migrate(client,'owned','local',emulator_host='http://127.0.0.1:9050',apply=True)=='verified' and not client.updates

@pytest.mark.parametrize('kind',['wrong_project','unexpected','type'])
def test_mismatched_existing_schema_never_mutates(monkeypatch,kind):
    client=Client()
    if kind=='wrong_project':client.table.project='unowned'
    elif kind=='unexpected':client.table.schema.append(bigquery.SchemaField('extra','STRING'))
    else:client.table.schema[0]=bigquery.SchemaField('outcome_id','INTEGER')
    with pytest.raises(ValueError):migrate(client,'owned','local',emulator_host='http://127.0.0.1:9050',apply=True)
    assert not client.updates

def test_metadata_success_but_select_failure_explicitly_refuses_success(monkeypatch):
    client=Client()
    def broken(*args,**kwargs):raise RuntimeError('private SDK body')
    monkeypatch.setattr('infra.migrate_outcomes.query_rows',broken)
    with pytest.raises(RuntimeError,match='not queryable') as caught:migrate(client,'owned','local',emulator_host='http://127.0.0.1:9050',apply=True)
    assert 'private SDK body' not in str(caught.value) and 'preserve' in str(caught.value).lower()


def test_cli_missing_emulator_guard_precedes_client_construction(monkeypatch):
    from infra import migrate_outcomes
    settings=SimpleNamespace(local_development=True,demo_mode=True,gcp_project='owned')
    monkeypatch.setattr(migrate_outcomes,'load_settings',lambda:settings)
    monkeypatch.setattr('sys.argv',['migrate_outcomes','--apply'])
    for name in ('FIRESTORE_EMULATOR_HOST','PUBSUB_EMULATOR_HOST','STORAGE_EMULATOR_HOST','BIGQUERY_EMULATOR_HOST'):monkeypatch.delenv(name,raising=False)
    constructed=[];monkeypatch.setattr('api.tools.cloud_events.create_analytics_client',lambda *_:constructed.append(True))
    with pytest.raises(ValueError):migrate_outcomes.main()
    assert constructed==[]
