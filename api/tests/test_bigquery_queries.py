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

@pytest.mark.parametrize('held_phase',['query','result','cleanup'])
def test_distinct_local_clients_serialize_through_result_cleanup(held_phase):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    first,job=fixture();second,_=fixture()
    entered,release,second_started,second_queried=Event(),Event(),Event(),Event()
    def hold(value):
        entered.set()
        assert release.wait(2), 'Test failed to release first query'
        return value
    if held_phase=='query':first.query.side_effect=lambda *a,**k:hold(job)
    elif held_phase=='result':job.result.side_effect=lambda **k:hold([{'value':7}])
    else:first.delete_dataset.side_effect=lambda *a,**k:hold(None)
    second.query.side_effect=lambda *a,**k:(second_queried.set(),second.query.return_value)[1]
    def run_second():
        second_started.set()
        return query_rows(second,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT,timeout=1)
    with ThreadPoolExecutor(max_workers=2) as pool:
        one=pool.submit(query_rows,first,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT,timeout=1)
        assert entered.wait(1)
        two=pool.submit(run_second)
        try:
            assert second_started.wait(1)
            assert not second_queried.wait(.1), 'Concurrent SDK query overlapped a local query/result/cleanup'
        finally:release.set()
        assert one.result(2).cleanup=='cleaned'
        assert two.result(2).cleanup=='cleaned'
        assert second_queried.is_set()


def test_local_query_wait_is_bounded_and_never_starts_sdk_when_busy():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic
    first,job=fixture();second,_=fixture();entered,release=Event(),Event()
    def hold(**kwargs):
        entered.set();assert release.wait(2)
        return [{'value':7}]
    job.result.side_effect=hold
    with ThreadPoolExecutor(max_workers=1) as pool:
        one=pool.submit(query_rows,first,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT,timeout=1)
        assert entered.wait(1)
        try:
            start=monotonic()
            with pytest.raises(TimeoutError,match='Local analytics query busy'):
                query_rows(second,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT,timeout=.05)
            assert monotonic()-start<.5
            second.query.assert_not_called()
        finally:release.set()
        assert one.result(2).cleanup=='cleaned'
    assert query_rows(second,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT).cleanup=='cleaned'


@pytest.mark.parametrize('failed_phase',['query','result','cleanup'])
def test_local_slot_released_after_each_failure_phase(failed_phase):
    first,job=fixture();second,_=fixture();error=RuntimeError('injected')
    if failed_phase=='query':first.query.side_effect=error
    elif failed_phase=='result':job.result.side_effect=error
    else:first.delete_dataset.side_effect=error
    if failed_phase=='cleanup':
        assert query_rows(first,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT).cleanup=='failed'
    else:
        with pytest.raises(RuntimeError) as caught:
            query_rows(first,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT)
        assert caught.value is error
    assert query_rows(second,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT,timeout=.05).cleanup=='cleaned'


def test_cloud_query_does_not_wait_for_local_emulator_slot():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    first,job=fixture();cloud,_=fixture();entered,release=Event(),Event()
    cloud._connection.API_BASE_URL='https://bigquery.googleapis.com'
    def hold(**kwargs):
        entered.set();assert release.wait(2)
        return [{'value':7}]
    job.result.side_effect=hold
    with ThreadPoolExecutor(max_workers=1) as pool:
        one=pool.submit(query_rows,first,'SELECT 7',project=PROJECT,emulator_endpoint=ENDPOINT,timeout=1)
        assert entered.wait(1)
        try:
            assert query_rows(cloud,'SELECT 7',project=PROJECT,timeout=.05).cleanup=='not_required'
            cloud.query.assert_called_once();cloud.delete_dataset.assert_not_called()
        finally:release.set()
        assert one.result(2).cleanup=='cleaned'
