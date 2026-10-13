#!/usr/bin/env python3
"""Inspect local application resources; create absent resources only with --apply."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from google.api_core.exceptions import NotFound,AlreadyExists,Conflict
from google.auth.credentials import AnonymousCredentials
from google.cloud import bigquery,pubsub_v1
from api.config import load_settings
from api.tools.cloud_events import create_analytics_client
from api.tools.storage import create_storage_client
from api.tools.emulators import loopback_endpoint

TABLES=('events','alerts','confirmations','evidence_ledger','outcomes')
ENDPOINTS={'FIRESTORE_EMULATOR_HOST':False,'PUBSUB_EMULATOR_HOST':False,'STORAGE_EMULATOR_HOST':True,'BIGQUERY_EMULATOR_HOST':True}


class LocalSetupError(ValueError):
    """Sanitized local validation failure."""

@contextmanager
def _close_clients():
    callbacks=[]
    try:yield callbacks
    finally:
        primary=sys.exception();failures=[]
        for callback in reversed(callbacks):
            try:callback()
            except Exception as error:failures.append(type(error).__name__)
        if failures:
            message='Local client closure failed: '+', '.join(failures)
            if primary is not None:primary.add_note(message)
            else:raise LocalSetupError(message)


def validate(settings,environment):
    if not settings.local_development or not settings.demo_mode:raise LocalSetupError('Explicit LOCAL_DEVELOPMENT=true and DEMO_MODE=true required')
    for name,http in ENDPOINTS.items():
        value=environment.get(name)
        if not value:raise LocalSetupError('Required local emulator endpoint: '+name)
        loopback_endpoint(value,http=http)
    project=settings.gcp_project
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',project):raise LocalSetupError('Explicit dedicated HighGround project required')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9._~-]{2,254}',settings.pubsub_topic):raise LocalSetupError('Invalid configured topic')
    if settings.pubsub_topic.lower().startswith('goog'):raise LocalSetupError('Reserved topic name')
    if settings.gcs_bucket!='highground-media-'+project:raise LocalSetupError('Local bucket must follow the configured-project media namespace')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,1023}',settings.bigquery_dataset):raise LocalSetupError('Invalid configured dataset')
    schemas={}
    for table in TABLES:
        fields=json.loads((ROOT/'infra/schemas'/f'{table}.json').read_text())
        if not isinstance(fields,list) or not fields:raise LocalSetupError('Invalid reviewed table schema')
        names=[]
        for field in fields:
            if not isinstance(field,dict) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',field.get('name','')) or field.get('mode','NULLABLE') not in ('NULLABLE','REQUIRED','REPEATED'):raise LocalSetupError('Invalid reviewed field schema')
            names.append(field['name'])
        if len(set(names))!=len(names):raise LocalSetupError('Duplicate reviewed schema fields')
        schemas[table]=tuple(bigquery.SchemaField.from_api_repr(field) for field in fields)
    return schemas


def signature(fields):
    aliases={'INT64':'INTEGER','FLOAT64':'FLOAT','BOOL':'BOOLEAN','STRUCT':'RECORD'}
    return sorted((field.name,aliases.get(field.field_type,field.field_type),field.mode,signature(field.fields)) for field in fields)


def optional(get):
    try:return get()
    except NotFound:return None


def inspect_all(settings,publisher,storage,analytics,schemas):
    project=settings.gcp_project;dataset=settings.bigquery_dataset
    topic=publisher.topic_path(project,settings.pubsub_topic)
    found_topic=optional(lambda:publisher.get_topic(request={'topic':topic},timeout=10,retry=None))
    if found_topic is not None and found_topic.name!=topic:raise LocalSetupError('Existing topic identity mismatch')
    bucket=optional(lambda:storage.get_bucket(settings.gcs_bucket,timeout=10,retry=None))
    if bucket is not None and bucket.name!=settings.gcs_bucket:raise LocalSetupError('Existing bucket identity mismatch')
    found_dataset=optional(lambda:analytics.get_dataset(f'{project}.{dataset}',timeout=10,retry=None))
    if found_dataset is not None and (found_dataset.project!=project or found_dataset.dataset_id!=dataset):raise LocalSetupError('Existing dataset identity mismatch')
    missing=[]
    if found_topic is None:missing.append(('topic',topic))
    if bucket is None:missing.append(('bucket',settings.gcs_bucket))
    if found_dataset is None:missing.append(('dataset',f'{project}.{dataset}'))
    for table in TABLES:
        identity=f'{project}.{dataset}.{table}'
        found=optional(lambda:analytics.get_table(identity,timeout=10,retry=None))
        if found is None:missing.append(('table',identity));continue
        if (found.project,found.dataset_id,found.table_id)!=(project,dataset,table) or signature(found.schema)!=signature(schemas[table]):raise LocalSetupError('Existing reviewed table is incompatible: '+table)
    return missing


def initialize(settings,*,apply=False):
    schemas=validate(settings,os.environ)
    # Client construction is deliberately after all local/name/schema validation.
    with _close_clients() as close:
        analytics=create_analytics_client(settings);close.append(analytics.close)
        storage=create_storage_client(settings);close.append(storage.close)
        publisher=pubsub_v1.PublisherClient(credentials=AnonymousCredentials());close.append(publisher.stop)
        if analytics.project!=settings.gcp_project or storage.project!=settings.gcp_project:raise LocalSetupError('Client project mismatch')
        missing=inspect_all(settings,publisher,storage,analytics,schemas)
        if apply:
            for kind,identity in missing:
                try:
                    if kind=='topic':publisher.create_topic(request={'name':identity},timeout=10,retry=None)
                    elif kind=='bucket':storage.create_bucket(identity,timeout=10,retry=None)
                    elif kind=='dataset':analytics.create_dataset(bigquery.Dataset(identity),timeout=10,retry=None)
                    else:analytics.create_table(bigquery.Table(identity,schema=schemas[identity.rsplit('.',1)[1]]),timeout=10,retry=None)
                except (AlreadyExists,Conflict):
                    # A concurrent create is acceptable only if a fresh full inspection agrees.
                    if (kind,identity) in inspect_all(settings,publisher,storage,analytics,schemas):raise LocalSetupError('Concurrent create could not be verified')
            remaining=inspect_all(settings,publisher,storage,analytics,schemas)
            if remaining:raise LocalSetupError('Local resource creation not verified')
        return {'mode':'apply' if apply else 'dry-run','missing_resources':len(missing),'verified':apply or not missing}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    try:print(json.dumps(initialize(load_settings(),apply=args.apply)))
    except Exception as error:
        print('Local initialization stopped: '+(str(error) if isinstance(error,LocalSetupError) else type(error).__name__),file=sys.stderr)
        sys.exit(1)
