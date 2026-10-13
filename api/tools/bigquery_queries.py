"""Bounded queries with exact, current-job emulator result cleanup only."""
from contextlib import contextmanager
from collections.abc import Iterator
from dataclasses import dataclass
from threading import Lock
from typing import Literal
from google.cloud import bigquery
from google.cloud.bigquery.table import Row
from api.tools.emulators import loopback_endpoint

Cleanup = Literal['not_required', 'cleaned', 'refused', 'failed']

# The local SQLite emulator cannot sustain overlapping query/result cleanup.
# One process-wide slot covers distinct SDK clients; cloud queries never take it.
_LOCAL_QUERY_LOCK = Lock()

@contextmanager
def _local_query_slot(enabled: bool, timeout: float) -> Iterator[None]:
    if not enabled:
        yield
        return
    if not _LOCAL_QUERY_LOCK.acquire(timeout=timeout):
        raise TimeoutError('Local analytics query busy')
    try:
        yield
    finally:
        _LOCAL_QUERY_LOCK.release()

@dataclass(frozen=True)
class QueryRows:
    rows: tuple[Row, ...]
    cleanup: Cleanup
    cleanup_error: str | None = None


def _cleanup(client: bigquery.Client, job: bigquery.QueryJob, project: str,
             enabled: bool, timeout: float) -> tuple[Cleanup, str | None]:
    if not enabled:return 'not_required', None
    destination=job.destination
    job_id=job.job_id
    if (not destination or not job_id or destination.project!=project
            or destination.dataset_id!=job_id or destination.table_id!=job_id):
        return 'refused', None
    try:
        client.delete_dataset(bigquery.DatasetReference(project,destination.dataset_id),
                              delete_contents=True,retry=None,timeout=timeout)
        return 'cleaned', None
    except Exception as error:
        # Only a class name is surfaced; SDK response bodies can contain private SQL/data.
        return 'failed', type(error).__name__


def query_rows(client: bigquery.Client, sql: str, *, project: str,
               emulator_endpoint: str | None = None, timeout: float = 10,
               job_config: bigquery.QueryJobConfig | None = None,
               max_results: int | None = None) -> QueryRows:
    """Materialize before cleanup; callers must surface failed/refused local cleanup.

    Validated emulator calls share a bounded in-process slot through cleanup.
    A busy slot raises before any SDK call; SDK request timeouts are unchanged.
    Production never takes this slot or deletes results. Query/result errors retain their original
    identity; an eligible known result is cleaned on failure, with cleanup status
    attached as an exception note. No destination lookup/listing is attempted.
    """
    if not project or client.project!=project:raise ValueError('Explicit client/project match required')
    if isinstance(timeout,bool) or not 0<timeout<=30:raise ValueError('Query timeout must be positive and at most 30 seconds')
    if max_results is not None and (type(max_results) is not int or not 1<=max_results<=10000):raise ValueError('Result bound must be an integer from 1 to 10000')
    if emulator_endpoint is not None:
        endpoint=loopback_endpoint(emulator_endpoint,http=True)
        actual=getattr(getattr(client,'_connection',None),'API_BASE_URL',None)
        if not isinstance(actual,str) or loopback_endpoint(actual,http=True)!=endpoint:raise ValueError('Emulator cleanup requires the actual matching loopback client endpoint')
    with _local_query_slot(emulator_endpoint is not None, timeout):
        query_options={'timeout':timeout,'retry':None,'job_retry':None}
        if job_config is not None:query_options['job_config']=job_config
        job=client.query(sql,**query_options)
        result_options={'timeout':timeout,'retry':None,'job_retry':None}
        if max_results is not None:result_options['max_results']=max_results
        try:
            rows=tuple(job.result(**result_options))
        except Exception as original:
            status,error=_cleanup(client,job,project,emulator_endpoint is not None,timeout)
            if status in ('failed','refused'):original.add_note('Local query-result cleanup: '+status+(' ('+error+')' if error else ''))
            raise
        status,error=_cleanup(client,job,project,emulator_endpoint is not None,timeout)
        return QueryRows(rows,status,error)
