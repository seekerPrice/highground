"""Bounded BigQuery stats over validated current synthetic identities."""
import math
import os
import logging
import re
from api.tools.bigquery_queries import query_rows
logger=logging.getLogger(__name__)
from google.cloud import bigquery
from api.dashboard_models import DashboardStats

def unavailable(shop_count: int) -> DashboardStats:
    return DashboardStats(status='unavailable',synthetic_shops=shop_count,alerts_accepted=None,average_alert_acceptance_ms=None,vehicles_reported_moved=None,estimated_stock_value_reported_lifted_rm=None)

class DashboardAnalytics:
    def __init__(self,client,project,dataset):
        if not all(p.replace('-','').replace('_','').isalnum() for p in (project,dataset)):raise ValueError('Invalid analytics identifiers')
        self.client,self.table,self.project=client,f'{project}.{dataset}',project
        self.last_cleanup_status='not_required'
    def stats(self,shops: list[dict],events: list[dict],alerts: list[dict],confirmations: list[dict],*,complete: bool) -> DashboardStats:
        if not complete:return unavailable(len(shops))
        shop_ids={s['shop_id'] for s in shops};event_ids={e['event_id'] for e in events}
        accepted={a['alert_id']:a for a in alerts if a.get('is_demo') is True and a.get('shop_id') in shop_ids and a.get('event_id') in event_ids and a.get('status')=='accepted'}
        virtual={a['alert_id'] for a in alerts if a.get('is_demo') is True and a.get('shop_id') in shop_ids and a.get('event_id') in event_ids and a.get('status')=='simulated' and a.get('delivery_provenance')=='local_virtual'}
        confirmed=[]
        for fact in confirmations:
            alert=accepted.get(fact.get('alert_id'))
            if not alert or fact.get('is_demo') is not True or fact.get('self_reported') is not True or not fact.get('episode_id') or fact.get('shop_id')!=alert['shop_id'] or fact.get('event_id')!=alert['event_id'] or fact.get('snapshot')!=alert.get('snapshot'):continue
            if fact.get('kind')=='stock':
                snapshot=fact.get('snapshot') or {};value=fact.get('protected_value_rm')
                if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1e9 or value!=round(sum(i.get('value_rm',0) for i in snapshot.get('items',[])),2) or snapshot.get('estimated_value_rm')!=value:continue
            elif fact.get('kind')!='vehicle':continue
            confirmed.append(fact['confirmation_id'])
        config=bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter('shops','STRING',sorted(shop_ids)),bigquery.ArrayQueryParameter('events','STRING',sorted(event_ids)),bigquery.ArrayQueryParameter('alerts','STRING',sorted(accepted)),bigquery.ArrayQueryParameter('confirmations','STRING',sorted(set(confirmed))),bigquery.ArrayQueryParameter('virtual_alerts','STRING',sorted(virtual))],maximum_bytes_billed=100_000_000)
        sql=f'''WITH accepted AS (
SELECT alert_id,MAX(latency_ms) latency_ms FROM `{self.table}.alerts`
WHERE is_demo=TRUE AND delivered=TRUE AND shop_id IN UNNEST(@shops) AND event_id IN UNNEST(@events) AND alert_id IN UNNEST(@alerts) GROUP BY alert_id),
virtual AS (SELECT alert_id FROM `{self.table}.alerts` WHERE is_demo=TRUE AND delivered=FALSE AND shop_id IN UNNEST(@shops) AND event_id IN UNNEST(@events) AND alert_id IN UNNEST(@virtual_alerts) GROUP BY alert_id),
confirmed AS (
SELECT confirmation_id,shop_id,episode_id,kind,MAX(protected_value_rm) value_rm FROM `{self.table}.confirmations`
WHERE is_demo=TRUE AND self_reported=TRUE AND shop_id IN UNNEST(@shops) AND event_id IN UNNEST(@events) AND confirmation_id IN UNNEST(@confirmations)
GROUP BY confirmation_id,shop_id,episode_id,kind),
stock AS (SELECT shop_id,episode_id,MAX(value_rm) value_rm FROM confirmed WHERE kind='stock' GROUP BY shop_id,episode_id),
vehicles AS (SELECT shop_id,episode_id FROM confirmed WHERE kind='vehicle' GROUP BY shop_id,episode_id)
SELECT (SELECT COUNT(*) FROM virtual) virtual_count,(SELECT COUNT(*) FROM accepted) alert_count,(SELECT COUNT(latency_ms) FROM accepted) latency_count,
(SELECT AVG(latency_ms) FROM accepted) latency_ms,(SELECT COUNT(*) FROM confirmed) confirmation_count,
(SELECT COUNT(*) FROM vehicles) vehicles,(SELECT COALESCE(SUM(value_rm),0) FROM stock) stock_value'''
        try:
            query=query_rows(self.client,sql,project=self.project,job_config=config,emulator_endpoint=os.environ.get('BIGQUERY_EMULATOR_HOST') or None,timeout=4,max_results=1)
            self.last_cleanup_status=query.cleanup
            if query.cleanup in ('failed','refused'):logger.warning('Dashboard local query cleanup: %s (%s)',query.cleanup,query.cleanup_error or 'none')
            rows=query.rows
            if len(rows)!=1:return unavailable(len(shops))
            row=rows[0]
            # Pending analytics outboxes are unavailable, never silently zero.
            if row['alert_count']!=len(accepted) or row['confirmation_count']!=len(set(confirmed)) or row['virtual_count']!=len(virtual):return unavailable(len(shops))
            latency=row['latency_ms'] if row['latency_count']==len(accepted) else None
            if latency is not None and (not math.isfinite(latency) or latency<0):return unavailable(len(shops))
            if not math.isfinite(row['stock_value']) or not 0<=row['stock_value']<=1e12:return unavailable(len(shops))
            return DashboardStats(status='available',synthetic_shops=len(shops),virtual_alerts_simulated=row['virtual_count'],alerts_accepted=row['alert_count'],average_alert_acceptance_ms=latency,vehicles_reported_moved=row['vehicles'],estimated_stock_value_reported_lifted_rm=round(row['stock_value'],2))
        except Exception as error:
            self.last_cleanup_status='query_failed'
            for note in getattr(error,'__notes__',[]):
                match=re.fullmatch(r'Local query-result cleanup: (failed|refused)(?: \([A-Za-z_][A-Za-z0-9_]*\))?',note)
                if match:
                    self.last_cleanup_status=match.group(1)
                    logger.warning('%s',note)
            logger.warning('Dashboard query unavailable: %s',type(error).__name__)
            return unavailable(len(shops))
    def close(self):self.client.close()
