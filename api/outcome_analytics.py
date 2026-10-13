"""Synthetic outcome coverage and actual immutable targeting decisions only."""
from datetime import UTC,datetime
import logging
from google.cloud import bigquery
from api.tools.bigquery_queries import query_rows
from api.outcome_models import OutcomeEpisode,OwnerOutcome,OutcomePrompt,OutcomeSummary,CalibrationState,CalibrationDecision,CalibrationAreaSummary,CalibrationHistoryPoint
from api.outcomes import outcome_coverage,response_matches_episode
from api.outcome_store import episode_key,FirestoreOutcomeStore
logger=logging.getLogger(__name__)

class OutcomeAnalytics:
    def __init__(self,client:bigquery.Client,project:str,dataset:str,store:FirestoreOutcomeStore,*,emulator_host:str|None=None):
        if not all(type(v) is str and v and v.replace('-','').replace('_','').isalnum() for v in (project,dataset)):raise ValueError('Invalid outcome analytics identifiers')
        self.client,self.project,self.table,self.store,self.emulator_host=client,project,f'{project}.{dataset}.outcomes',store,emulator_host
        self.last_cleanup_status='not_required'
    @staticmethod
    def _fact(response:OwnerOutcome,episode:OutcomeEpisode)->dict:
        if not response_matches_episode(response,episode) or response.response_id!=episode_key(episode):raise ValueError('Outcome episode mismatch')
        accepted=[r for r in episode.deliveries if r.status=='accepted' and r.provenance=='telegram_api' and r.accepted_at<=response.answered_at]
        reference=min(accepted,key=lambda r:r.accepted_at) if accepted else None
        return dict(outcome_id=response.response_id,alert_id=reference.alert_id if reference else None,event_id=None,shop_id=response.shop_id,outcome=response.answer,depth_cm=response.depth_cm,outcome_at=response.answered_at.astimezone(UTC).isoformat(),is_demo=response.is_demo,episode_id=response.episode_id,area=response.area,reference_basis=response.reference_basis,reference_at=response.observed_at.astimezone(UTC).isoformat(),answered_at=response.answered_at.astimezone(UTC).isoformat(),entrypoint=response.entrypoint,origin=response.origin,scenario_generation=response.scenario_generation)
    def insert_outcome(self,response:OwnerOutcome,episode:OutcomeEpisode)->None:
        row=self._fact(response,episode)
        errors=self.client.insert_rows_json(self.table,[row],row_ids=[response.response_id],retry=None,timeout=5)
        if errors:raise RuntimeError('Outcome analytics insertion unavailable')
    def _rows(self,kind):
        rows=list(self.store.client.collection(self.store.prefix+'outcome_'+kind).limit(1001).stream(timeout=5,retry=None))
        if len(rows)>1000:raise ValueError('Outcome source scope overflow')
        return rows
    def summary(self,synthetic_shops:list[dict],generation:int,now:datetime)->OutcomeSummary:
        def unavailable():return OutcomeSummary(status='unavailable',generated_at=now,note='Synthetic outcome summary is unavailable. Missing data does not establish no water.')
        if now.tzinfo is None or now.utcoffset() is None:raise ValueError('Aware outcome clock required')
        try:
            if type(generation) is not int or generation<0 or len(synthetic_shops)>50:raise ValueError('Invalid synthetic scope')
            ids={s['shop_id'] for s in synthetic_shops if s.get('is_demo') is True}
            if len(ids)!=len(synthetic_shops):raise ValueError('Unverified synthetic scope')
            episodes=tuple(OutcomeEpisode.model_validate_json(r.to_dict()['json']) for r in self._rows('episodes'))
            episodes=tuple(e for e in episodes if e.is_demo and e.scenario_generation==generation and e.shop_id in ids)
            if any(e.history_status!='complete' or e.started_at>now or (e.closed_at is not None and e.closed_at>now) for e in episodes):raise ValueError('Incomplete outcome episode history')
            ep_by_key={episode_key(e):e for e in episodes}
            if len(ep_by_key)!=len(episodes):raise ValueError('Duplicate confirmed episode')
            responses=[]
            for row in self._rows('responses'):
                response=OwnerOutcome.model_validate_json(row.to_dict()['json']);ep=ep_by_key.get(row.id)
                if ep is None:continue
                if not response_matches_episode(response,ep) or response.answered_at>now:raise ValueError('Outcome provenance mismatch')
                responses.append(response)
            ep_by_scope={(e.shop_id,e.episode_id):e for e in episodes}
            expected={r.response_id:self._fact(r,ep_by_scope[r.shop_id,r.episode_id]) for r in responses}
            config=bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter('ids','STRING',sorted(expected)),bigquery.ArrayQueryParameter('shops','STRING',sorted(ids)),bigquery.ScalarQueryParameter('generation','INT64',generation)],maximum_bytes_billed=100_000_000)
            result=query_rows(self.client,f'SELECT * FROM `{self.table}` WHERE is_demo=TRUE AND scenario_generation=@generation AND shop_id IN UNNEST(@shops) AND outcome_id IN UNNEST(@ids)',project=self.project,emulator_endpoint=self.emulator_host,timeout=5,job_config=config,max_results=1001)
            self.last_cleanup_status=result.cleanup
            if result.cleanup in ('failed','refused'):
                logger.warning('Outcome local query cleanup: %s',result.cleanup)
                return unavailable()
            if len(result.rows)>1000:raise ValueError('Outcome analytics scope overflow')
            actual={}
            for row in result.rows:
                value=dict(row);identity=value.get('outcome_id')
                if identity not in expected:raise ValueError('Unexpected outcome fact')
                normalized={k:(v.isoformat() if isinstance(v,datetime) else v) for k,v in value.items()}
                for k in ('outcome_at','reference_at','answered_at'):
                    if normalized.get(k) is not None:normalized[k]=datetime.fromisoformat(normalized[k].replace('Z','+00:00')).astimezone(UTC).isoformat()
                if normalized!=expected[identity] or (identity in actual and actual[identity]!=normalized):raise ValueError('Conflicting outcome facts')
                actual[identity]=normalized
            if actual.keys()!=expected.keys():raise ValueError('Pending outcome analytics')
            prompts=[]
            for row in self._rows('prompts'):
                p=row.to_dict();ep=ep_by_key.get(row.id)
                if ep is None:continue
                status=p['status'];status='pending' if status=='preparing' else status
                prompts.append(OutcomePrompt(shop_id=ep.shop_id,episode_id=ep.episode_id,is_demo=True,scenario_generation=generation,status=status,provenance=p.get('provenance','local_virtual' if status=='simulated' else 'telegram_api')))
            allowed_areas={e.area for e in episodes}
            history={}
            for row in self._rows('calibration_facts'):
                raw=row.to_dict()
                if raw.get('is_demo') is not True or raw.get('scenario_generation')!=generation or raw.get('area') not in allowed_areas:continue
                decision=CalibrationDecision.model_validate_json(raw['json']);at=raw['evaluated_at']
                if at>now or at!=decision.window_end:raise ValueError('Invalid calibration timestamp')
                history.setdefault(raw['area'],[]).append(CalibrationHistoryPoint(evaluated_at=at,old_multiplier=decision.old_multiplier,new_multiplier=decision.new_multiplier,reason=decision.reason,response_count=decision.response_count,water_response_count=decision.water_response_count,fixture_response_count=decision.fixture_response_count))
            states=[]
            for row in self._rows('calibration'):
                state=CalibrationState.model_validate_json(row.to_dict()['json'])
                if state.is_demo and state.scenario_generation==generation and state.area in allowed_areas:states.append(state)
            if len(states)>50 or len({s.area for s in states})!=len(states) or set(history)-{s.area for s in states}:raise ValueError('Calibration scope unavailable')
            points=sorted(((h.evaluated_at,area,h) for area,items in history.items() for h in items),key=lambda r:r[0],reverse=True);selected=points[:50]
            areas=tuple(CalibrationAreaSummary(area=s.area,multiplier=s.multiplier,version=s.version,evaluated_at=max((h.evaluated_at for h in history.get(s.area,[])),default=None),history=tuple(h for _,area,h in selected if area==s.area)) for s in sorted(states,key=lambda s:s.area))
            coverage=outcome_coverage(episodes,tuple(responses),tuple(prompts),synthetic_shop_ids=ids,generation=generation)
            return OutcomeSummary(status='available' if episodes or areas else 'empty',generated_at=now,scenario_generation=generation,registered_synthetic_shops=len(ids),coverage=coverage,calibration_areas=areas,history_truncated=len(points)>50,note='Synthetic owner reports and targeting decisions. Seeded and virtual records are not Telegram acceptance or forecasting accuracy.')
        except Exception as error:
            logger.warning('Outcome summary unavailable: %s',type(error).__name__)
            return unavailable()
    def close(self)->None:self.client.close()
