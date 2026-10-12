"""Official Pub/Sub and BigQuery clients with explicit local-only emulators.

Streaming insert IDs and publish retries are best-effort. Consumers/aggregates
must dedupe the stable event_id/alert_id; no exactly-once promise is made.
"""
import json
import os
from typing import TYPE_CHECKING

import google.auth
from google.api_core.client_options import ClientOptions
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery, pubsub_v1

from api.tools.emulators import loopback_endpoint

if TYPE_CHECKING:
    from api.config import Settings




def _adc(settings: 'Settings'):
    if not settings.gcp_project.strip():
        raise ValueError('GCP_PROJECT is required for event sinks')
    credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'],
                                         quota_project_id=settings.gcp_project)
    return credentials


def create_event_sinks(settings: 'Settings') -> 'GoogleEventSinks':
    if not settings.gcp_project.strip():
        raise ValueError('GCP_PROJECT is required for event sinks')
    pubsub_host = os.environ.get('PUBSUB_EMULATOR_HOST')
    bq_host = os.environ.get('BIGQUERY_EMULATOR_HOST')
    if pubsub_host:
        loopback_endpoint(pubsub_host)
        publisher = pubsub_v1.PublisherClient(credentials=AnonymousCredentials())
    else:
        publisher = pubsub_v1.PublisherClient(credentials=_adc(settings))
    if bq_host:
        endpoint = loopback_endpoint(bq_host, http=True)
        analytics = bigquery.Client(project=settings.gcp_project, credentials=AnonymousCredentials(),
                                    client_options=ClientOptions(api_endpoint=endpoint))
    else:
        analytics = bigquery.Client(project=settings.gcp_project, credentials=_adc(settings))
    return GoogleEventSinks(publisher, analytics, settings.gcp_project,
                            settings.pubsub_topic, settings.bigquery_dataset)


class GoogleEventSinks:
    def __init__(self, publisher: pubsub_v1.PublisherClient, analytics: bigquery.Client,
                 project: str, topic: str, dataset: str) -> None:
        self.publisher, self.analytics = publisher, analytics
        self.topic = publisher.topic_path(project, topic)
        self.dataset = f'{project}.{dataset}'

    def publish_event(self, event: dict) -> None:
        public = {key: event[key] for key in ('event_id','source','level','lat','lng','radius_m',
                                             'confidence','reason','created_at','is_demo')}
        public['created_at'] = public['created_at'].isoformat()
        future = self.publisher.publish(self.topic, json.dumps(public, allow_nan=False).encode(),
                                        retry=None, timeout=8, event_id=event['event_id'])
        future.result(timeout=10)

    def insert_event(self, event: dict) -> None:
        row = {key: event[key] for key in ('event_id','source','level','lat','lng','radius_m',
                                         'confidence','reason','created_at','is_demo')}
        row['created_at'] = row['created_at'].isoformat()
        self._insert('events', row, event['event_id'])

    def insert_alert(self, alert: dict) -> None:
        row = {key: alert[key] for key in ('alert_id','event_id','shop_id','telegram_chat_id_hash',
                                         'level','language','is_demo')}
        row.update(sent_at=alert.get('sent_at').isoformat() if alert.get('sent_at') else None,
                   delivered=alert['status'] == 'accepted', latency_ms=alert.get('latency_ms'))
        self._insert('alerts', row, alert['alert_id'])

    def insert_confirmation(self, confirmation: dict) -> None:
        row = {key: confirmation[key] for key in ('confirmation_id', 'action_id', 'episode_id', 'alert_id',
                                                  'event_id', 'shop_id', 'kind', 'protected_value_rm', 'is_demo')}
        row['confirmed_at'] = confirmation['confirmed_at'].isoformat()
        row['self_reported'] = True
        self._insert('confirmations', row, confirmation['confirmation_id'])

    def _insert(self, table: str, row: dict, row_id: str) -> None:
        errors = self.analytics.insert_rows_json(f'{self.dataset}.{table}', [row], row_ids=[row_id], timeout=10, retry=None)
        if errors:
            raise RuntimeError('Analytics rejected a row')

    def close(self) -> None:
        self.publisher.stop()
        self.analytics.close()


def deduped_alert_counts_sql(project: str, dataset: str) -> str:
    """Task 15 must aggregate logical IDs rather than physical streamed rows."""
    if not all(part.replace('-', '').replace('_', '').isalnum() for part in (project, dataset)):
        raise ValueError('Invalid analytics identifier')
    return (f'SELECT COUNT(DISTINCT alert_id) AS alerts_accepted FROM `{project}.{dataset}.alerts` '
            'WHERE delivered = TRUE AND is_demo = TRUE')
