"""Add reviewed nullable outcome columns locally; never drop or replace tables."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from google.cloud import bigquery
from api.config import load_settings
from api.tools.emulators import loopback_endpoint
from api.tools.bigquery_queries import query_rows
from infra.seed_outcomes import require_local


def migrate(client,project:str,dataset:str,*,emulator_host:str,apply:bool=False)->str:
    if not all(type(v) is str and v and v.replace('-','').replace('_','').isalnum() for v in (project,dataset)):raise ValueError('Explicit owned analytics identifiers required')
    endpoint=loopback_endpoint(emulator_host,http=True)
    actual=getattr(getattr(client,'_connection',None),'API_BASE_URL',None)
    if client.project!=project or not isinstance(actual,str) or loopback_endpoint(actual,http=True)!=endpoint:raise ValueError('Actual matching local client required before mutation')
    reviewed=json.loads((Path(__file__).resolve().parent/'schemas/outcomes.json').read_text())
    expected=tuple((r['name'],r['type'],r['mode']) for r in reviewed)
    if len(expected)!=16 or any(mode!='NULLABLE' for _,_,mode in expected):raise ValueError('Reviewed additive schema required')
    table=client.get_table(f'{project}.{dataset}.outcomes',retry=None,timeout=5)
    if (table.project,table.dataset_id,table.table_id)!=(project,dataset,'outcomes'):raise ValueError('Owned outcome table identity mismatch')
    existing=tuple((r.name,r.field_type,r.mode) for r in table.schema)
    if existing not in (expected[:8],expected):raise ValueError('Existing outcome schema differs; no mutation permitted')
    if not apply:return 'pending' if len(existing)==8 else 'metadata_ready'
    if len(existing)==8:
        table.schema=[bigquery.SchemaField.from_api_repr(row) for row in reviewed]
        client.update_table(table,['schema'],retry=None,timeout=5)
    columns=','.join(f'`{name}`' for name,_,_ in expected[8:])
    try:
        result=query_rows(client,f'SELECT {columns} FROM `{project}.{dataset}.outcomes` LIMIT 1',project=project,emulator_endpoint=endpoint,timeout=5,max_results=1)
        if result.cleanup!='cleaned':raise RuntimeError('Local result cleanup incomplete')
    except Exception:
        raise RuntimeError('Outcome columns are not queryable or verification could not finish. No table/data was deleted. Preserve the existing table and rows; have the operator inspect the emulator and prepare a separately named compatible dataset with verified copy before changing configuration.') from None
    return 'verified'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    settings=load_settings();require_local(settings,os.environ)
    from api.tools.cloud_events import create_analytics_client
    client=create_analytics_client(settings)
    try:result=migrate(client,settings.gcp_project,settings.bigquery_dataset,emulator_host=os.environ['BIGQUERY_EMULATOR_HOST'],apply=args.apply)
    finally:client.close()
    print('Outcome schema: '+result+'. Dry-run metadata is not queryability acceptance.' if not args.apply else 'Outcome schema: '+result+'. Existing data preserved.')
if __name__=='__main__':main()
