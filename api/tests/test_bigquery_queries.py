"""Query-result lifecycle contracts, with one explicitly local SDK acceptance."""
from types import SimpleNamespace
from unittest.mock import Mock
import os
import sys
import pytest
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from api.tools.bigquery_queries import query_rows

ENDPOINT='http://127.0.0.1:9050'
PROJECT='highground-query-lifecycle-test'

def fixture():
    client=Mock();client.project=PROJECT;client._connection=SimpleNamespace(API_BASE_URL=ENDPOINT)
    job=Mock();job.job_id='unique_job';job.destination=bigquery.TableReference(bigquery.DatasetReference(PROJECT,'unique_job'),'unique_job')
    job.result.return_value=[{'value':7}];client.query.return_value=job
    return client,job

def test_materializes_before_exact_own_destination_cleanup():
    client,job=fixture();sequence=[]
    def rows():
        assert not sequence
        sequence.append('read')
        yield {'value':7}
    job.result.return_value=rows()
    client.delete_dataset.side_effect=lambda *args,**kwargs:sequence.append('cleanup')
    result=query_rows(client,'SELECT 7 AS value',project=PROJECT,emulator_endpoint=ENDPOINT)
    assert result.rows==({'value':7},) and result.cleanup=='cleaned'
    client.query.assert_called_once_with('SELECT 7 AS value',timeout=10,retry=None,job_retry=None)
    job.result.assert_called_once_with(timeout=10,retry=None,job_retry=None)
    args,kwargs=client.delete_dataset.call_args
    assert args==(bigquery.DatasetReference(PROJECT,'unique_job'),)
    assert kwargs=={'delete_contents':True,'timeout':10,'retry':None}
    assert sequence==['read','cleanup']

@pytest.mark.parametrize('mismatch',['project','dataset','table','production','client_endpoint'])
def test_never_cleans_unowned_or_production_results(mismatch):
    client,job=fixture();endpoint=ENDPOINT
    if mismatch=='project':job.destination=bigquery.TableReference(bigquery.DatasetReference('other','unique_job'),'unique_job')
    if mismatch=='dataset':job.destination=bigquery.TableReference(bigquery.DatasetReference(PROJECT,'other'),'unique_job')
    if mismatch=='table':job.destination=bigquery.TableReference(bigquery.DatasetReference(PROJECT,'unique_job'),'other')
    if mismatch=='production':endpoint=None
    if mismatch=='client_endpoint':client._connection.API_BASE_URL='https://bigquery.googleapis.com'
    if mismatch=='client_endpoint':
        with pytest.raises(ValueError):query_rows(client,'SELECT 7',project=PROJECT,emulator_endpoint=endpoint)
        client.query.assert_not_called()
    else:
        result=query_rows(client,'SELECT 7',project=PROJECT,emulator_endpoint=endpoint)
        assert result.cleanup in ('refused','not_required')
    client.delete_dataset.assert_not_called()

def test_cleanup_failure_preserves_materialized_rows_and_is_observable():
    client,job=fixture();client.delete_dataset.side_effect=RuntimeError('private body')
    result=query_rows(client,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT)
    assert result.rows==({'value':7},) and result.cleanup=='failed' and result.cleanup_error=='RuntimeError'
    assert 'private body' not in repr(result)

def test_result_failure_cleans_only_known_destination_without_hiding_original():
    client,job=fixture();error=RuntimeError('result failed');job.result.side_effect=error
    with pytest.raises(RuntimeError) as caught:query_rows(client,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT)
    assert caught.value is error;client.delete_dataset.assert_called_once()
    client.delete_dataset.side_effect=ValueError('cleanup failed')
    with pytest.raises(RuntimeError) as caught:query_rows(client,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT)
    assert caught.value is error and any('ValueError' in note for note in error.__notes__)

def test_query_failure_has_no_known_destination_to_delete():
    client,job=fixture();error=RuntimeError('query failed');client.query.side_effect=error
    with pytest.raises(RuntimeError) as caught:query_rows(client,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT)
    assert caught.value is error;client.delete_dataset.assert_not_called()

def test_parameterized_query_config_and_result_bound_are_preserved():
    client,job=fixture()
    config=bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter('value','INT64',7)],maximum_bytes_billed=100000)
    query_rows(client,'SELECT @value',project=PROJECT,emulator_endpoint=ENDPOINT,job_config=config,max_results=1)
    assert client.query.call_args.kwargs['job_config'] is config
    assert job.result.call_args.kwargs['max_results']==1

def test_cloud_endpoint_cannot_select_emulator_cleanup():
    client,job=fixture()
    with pytest.raises(ValueError):query_rows(client,'SELECT 7',project=PROJECT,emulator_endpoint='https://bigquery.googleapis.com')
    client.query.assert_not_called()

@pytest.mark.skipif(not os.environ.get('BIGQUERY_EMULATOR_HOST'),reason='Local BigQuery emulator required')
def test_actual_sdk_own_result_removed_after_materialization():
    project=os.environ.get('GCP_PROJECT','highground-2026-lucas')
    endpoint=os.environ['BIGQUERY_EMULATOR_HOST']
    from api.tools.emulators import loopback_endpoint
    endpoint=loopback_endpoint(endpoint,http=True)
    client=bigquery.Client(project=project,credentials=AnonymousCredentials(),client_options=ClientOptions(api_endpoint=endpoint))
    original=client.query;destinations=[]
    def capture(*args,**kwargs):
        job=original(*args,**kwargs);destinations.append(job);return job
    client.query=capture
    try:
        result=query_rows(client,'SELECT 7 AS value',project=project,emulator_endpoint=endpoint)
        assert result.rows[0]['value']==7 and result.cleanup=='cleaned'
        destination=destinations[0].destination
        with pytest.raises(NotFound):client.get_dataset(bigquery.DatasetReference(project,destination.dataset_id),retry=None,timeout=10)
    finally:
        primary=sys.exception()
        try:
            if destinations:
                job=destinations[0];destination=job.destination
                if destination and destination.project==project and destination.dataset_id==destination.table_id==job.job_id:
                    try:client.delete_dataset(bigquery.DatasetReference(project,destination.dataset_id),delete_contents=True,retry=None,timeout=10)
                    except NotFound:pass
                    except Exception as cleanup_error:
                        if primary is not None:primary.add_note('Acceptance cleanup failed: '+type(cleanup_error).__name__)
                        else:raise
        finally:client.close()
