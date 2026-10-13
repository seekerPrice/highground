"""Bounded outcome transactions. Network delivery and clocks belong to callers."""
from datetime import datetime
from hashlib import sha256
from google.cloud import firestore
from api.agents.sessions import session_user_id
from api.active_risk import ActiveRiskStore
from api.demo_scenario import scenario_collection
from api.outcome_models import OutcomeEpisode,OwnerOutcome,CalibrationState,CalibrationEvidence
from api.outcomes import first_owner_response
from api.calibration import decide_calibration,outcome_key


def episode_key(episode:OutcomeEpisode)->str:
    return sha256(f'{episode.is_demo}:{episode.scenario_generation}:{episode.shop_id}:{episode.episode_id}'.encode()).hexdigest()


class FirestoreOutcomeStore:
    def __init__(self,client,hash_salt:str,*,prefix='',shops='shops',risks='active_risks'):
        if not hash_salt:raise ValueError('Outcome identity hashing required')
        self.client,self.salt,self.prefix,self.shops,self.risks=client,hash_salt,prefix,shops,risks
    def _ref(self,kind,key):
        if type(key) is not str or not key or len(key)>160 or '/' in key:raise ValueError('Invalid outcome record identity')
        return self.client.collection(self.prefix+'outcome_'+kind).document(key)
    @staticmethod
    def _read(ref,tx=None):return ref.get(transaction=tx,timeout=5,retry=None).to_dict() or {}
    @staticmethod
    def _clock(now):
        if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None:raise ValueError('Outcome clock must be aware')
    @staticmethod
    def _calibration_key(area:str,is_demo:bool,generation:int|None)->str:
        # Domain validation keeps realm and generation semantics in one place.
        CalibrationState(area=area,is_demo=is_demo,scenario_generation=generation)
        return sha256(f'{is_demo}:{generation}:{area}'.encode()).hexdigest()

    def calibration_state(self,area:str,*,is_demo:bool,generation:int|None,transaction=None)->CalibrationState|None:
        row=self._read(self._ref('calibration',self._calibration_key(area,is_demo,generation)),transaction)
        return CalibrationState.model_validate_json(row['json']) if row else None

    def pending_fact_keys(self,limit:int=20)->tuple[str,...]:
        from google.cloud.firestore_v1.base_query import FieldFilter
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Invalid outcome fact budget')
        rows=self.client.collection(self.prefix+'outcome_facts').where(filter=FieldFilter('bigquery','==','pending')).limit(limit).stream(timeout=5,retry=None)
        return tuple(row.id for row in rows)

    def pending_fact(self,key:str)->OwnerOutcome|None:
        row=self._read(self._ref('facts',key))
        return OwnerOutcome.model_validate_json(row['json']) if row and row.get('bigquery')!='done' else None

    def acknowledge_fact(self,key:str,expected:OwnerOutcome,*,transaction=None)->None:
        ref=self._ref('facts',key)
        def mark(tx):
            current=self._read(ref,tx)
            if current.get('json')!=expected.model_dump_json():raise ValueError('Outcome fact changed')
            if current.get('bigquery')!='done':tx.set(ref,{**current,'bigquery':'done'})
        if transaction is not None:mark(transaction)
        else:firestore.transactional(mark)(self.client.transaction(max_attempts=5))

    def register_episode(self,episode:OutcomeEpisode)->str:
        """Input is trusted adapter history, never a request-body episode."""
        key=episode_key(episode);ref=self._ref('episodes',key)
        @firestore.transactional
        def save(tx):
            old=self._read(ref,tx)
            if old:
                previous=OutcomeEpisode.model_validate_json(old['json'])
                if (previous.started_at,previous.area)!=(episode.started_at,episode.area):raise ValueError('Confirmed episode identity conflict')
                if previous.closed_at is not None and previous.closed_at!=episode.closed_at:raise ValueError('Explicit closure is immutable')
                previous_deliveries={row.alert_id:row for row in previous.deliveries}
                incoming={row.alert_id:row for row in episode.deliveries}
                if not previous_deliveries.keys()<=incoming.keys():raise ValueError('Delivery history cannot be removed')
                for identity,row in previous_deliveries.items():
                    if row.accepted_at is not None and incoming[identity]!=row:raise ValueError('Accepted delivery is immutable')
            tx.set(ref,{'json':episode.model_dump_json(),'is_demo':episode.is_demo,'scenario_generation':episode.scenario_generation})
            return key
        return save(self.client.transaction(max_attempts=5))
    def episode(self,key:str)->OutcomeEpisode|None:
        value=self._read(self._ref('episodes',key))
        return OutcomeEpisode.model_validate_json(value['json']) if value else None
    def record_response(self,key:str,*,sender_chat_id:int,answer:str,observed_at:datetime,now:datetime,depth_cm:int|None=None,entrypoint='alert_response')->OwnerOutcome:
        self._clock(now);self._clock(observed_at)
        if type(sender_chat_id) is not int:raise ValueError('Owner identity required')
        actor=session_user_id(sender_chat_id,self.salt)
        episode_ref=self._ref('episodes',key);response_ref=self._ref('responses',key);fact_ref=self._ref('facts',key)
        @firestore.transactional
        def record(tx):
            stored=self._read(episode_ref,tx)
            if not stored:raise ValueError('Confirmed episode unavailable')
            ep=OutcomeEpisode.model_validate_json(stored['json'])
            shop=self._read(self.client.collection(self.shops).document(ep.shop_id),tx)
            risk=self._read(self.client.collection(self.risks).document(ep.shop_id),tx)
            scenario=self._read(self.client.collection(scenario_collection(self.shops)).document('current'),tx) if ep.is_demo else {}
            previous=self._read(response_ref,tx)
            owners=[r for r in shop.get('recipients',[]) if r.get('role')=='owner']
            if len(owners)!=1 or owners[0].get('telegram_chat_id')!=sender_chat_id or shop.get('is_demo',False)!=ep.is_demo:raise ValueError('Current owner required')
            if ep.is_demo and (scenario.get('state','ready')!='ready' or scenario.get('generation',0)!=ep.scenario_generation):raise ValueError('Obsolete outcome generation')
            if ActiveRiskStore._view(risk,shop).active_danger:raise ValueError('Outcome collection deferred during Danger')
            if ep.closed_at is None and risk.get('episode_id')!=ep.episode_id:raise ValueError('Open episode no longer current')
            response=first_owner_response(OwnerOutcome.model_validate_json(previous['json']) if previous else None,ep,
                actor_hash=actor,actor_shop_id=ep.shop_id,actor_role='owner',current_owner_hash=actor,
                answer=answer,observed_at=observed_at,answered_at=now,depth_cm=depth_cm,entrypoint=entrypoint)
            if not previous:
                tx.create(response_ref,{'json':response.model_dump_json(),'created_at':now})
                tx.create(fact_ref,{'json':response.model_dump_json(),'bigquery':'pending'})
            return response
        return record(self.client.transaction(max_attempts=5))
    def calibrate(self,expected:CalibrationState,evidence:tuple[CalibrationEvidence,...],*,now:datetime,deadline=None):
        from api.outcome_history import OutcomeHistoryAdapter
        OutcomeHistoryAdapter._deadline(deadline)
        self._clock(now)
        if len(evidence)>100:raise ValueError('Calibration transaction scope exceeds100')
        key=self._calibration_key(expected.area,expected.is_demo,expected.scenario_generation)
        state_ref=self._ref('calibration',key)
        receipts={outcome_key(row.response):self._ref('consumed',outcome_key(row.response)) for row in evidence}
        def read(ref,tx):
            OutcomeHistoryAdapter._deadline(deadline)
            return self._read(ref,tx)
        @firestore.transactional
        def commit(tx):
            old=read(state_ref,tx)
            current=CalibrationState.model_validate_json(old['json']) if old else CalibrationState(area=expected.area,is_demo=expected.is_demo,scenario_generation=expected.scenario_generation)
            consumed=frozenset(identity for identity,ref in receipts.items() if read(ref,tx))
            scenario=read(self.client.collection(scenario_collection(self.shops)).document('current'),tx) if current.is_demo else {}
            if current.is_demo and (scenario.get('state','ready')!='ready' or scenario.get('generation',0)!=current.scenario_generation):raise ValueError('Obsolete calibration generation')
            for row in evidence:
                OutcomeHistoryAdapter._deadline(deadline)
                stored_ep=read(self._ref('episodes',episode_key(row.episode)),tx)
                stored_response=read(self._ref('responses',episode_key(row.episode)),tx)
                if not stored_ep or not stored_response or OutcomeEpisode.model_validate_json(stored_ep['json'])!=row.episode or OwnerOutcome.model_validate_json(stored_response['json'])!=row.response:raise ValueError('Calibration requires exact persisted evidence')
            OutcomeHistoryAdapter._deadline(deadline)
            if current!=expected:raise ValueError('Calibration version conflict')
            decision=decide_calibration(current,evidence,now=now,consumed_keys=consumed)
            if decision.new_version==current.version:return decision
            next_state=current.model_copy(update={'version':decision.new_version,'multiplier':decision.new_multiplier})
            tx.set(state_ref,{'json':next_state.model_dump_json(),'area':current.area,'is_demo':current.is_demo,'scenario_generation':current.scenario_generation})
            for identity in decision.consumed_outcome_keys:
                tx.create(receipts[identity],{'area':current.area,'version':decision.new_version,'consumed_at':now})
            tx.create(self._ref('calibration_facts',f'{key}-{decision.new_version}'),{'json':decision.model_dump_json(),'area':current.area,'is_demo':current.is_demo,'scenario_generation':current.scenario_generation,'evaluated_at':now})
            return decision
        return commit(self.client.transaction(max_attempts=5))

    def claim_prompt(self,key:str,*,now:datetime,ask_after_hours:float=6.)->dict:
        """Prepare only; sending requires another final transactional guard."""
        from datetime import timedelta
        from uuid import uuid4
        self._clock(now);ref=self._ref('prompts',key);owner=uuid4().hex;candidate_token=uuid4().hex
        @firestore.transactional
        def claim(tx):
            row=self._read(ref,tx);ep,recipient,reason=self._prompt_context(key,tx,now,ask_after_hours)
            if row.get('status') in ('accepted','simulated','uncertain','superseded'):return row
            if row.get('status')=='sending':
                if row['lease_until']>now:return {'status':'busy'}
                updated={**row,'status':'uncertain','lease_until':now}
                tx.set(ref,updated);return updated
            if reason!='due':
                if row and reason in ('obsolete_scenario','already_answered','unavailable'):
                    tx.set(ref,{**row,'status':'superseded','lease_until':now})
                return {'status':reason}
            if row.get('lease_until',now)>now:return {'status':'busy'}
            token=row.get('callback_token') or candidate_token
            token_ref=self._ref('tokens',token);binding=self._read(token_ref,tx)
            expected={'episode_key':key,'owner_hash':session_user_id(recipient,self.salt),'is_demo':ep.is_demo,'scenario_generation':ep.scenario_generation}
            if binding and binding!=expected:raise ValueError('Outcome token collision or owner changed')
            if not binding:tx.create(token_ref,expected)
            updated={'callback_token':token,'status':'preparing','owner':owner,'lease_until':now+timedelta(seconds=60),
                     'owner_hash':session_user_id(recipient,self.salt),'is_demo':ep.is_demo,'scenario_generation':ep.scenario_generation}
            tx.set(ref,updated)
            return {**updated,'recipient_chat_id':recipient}
        return claim(self.client.transaction(max_attempts=5))

    def _prompt_context(self,key,tx,now,ask_after_hours):
        from api.outcomes import prompt_due
        value=self._read(self._ref('episodes',key),tx)
        if not value:raise ValueError('Confirmed episode unavailable')
        ep=OutcomeEpisode.model_validate_json(value['json'])
        shop=self._read(self.client.collection(self.shops).document(ep.shop_id),tx)
        risk=self._read(self.client.collection(self.risks).document(ep.shop_id),tx)
        scenario=self._read(self.client.collection(scenario_collection(self.shops)).document('current'),tx) if ep.is_demo else {}
        response=self._read(self._ref('responses',key),tx)
        owners=[r for r in shop.get('recipients',[]) if r.get('role')=='owner']
        recipient=owners[0].get('telegram_chat_id') if len(owners)==1 else None
        if type(recipient) is not int:recipient=None
        if response:return ep,recipient,'already_answered'
        if shop.get('is_demo',False)!=ep.is_demo:return ep,recipient,'unavailable'
        if ep.is_demo and scenario.get('state','ready')!='ready':return ep,recipient,'obsolete_scenario'
        if ep.closed_at is None and risk.get('episode_id')!=ep.episode_id:return ep,recipient,'unavailable'
        decision=prompt_due(ep,now,current_owner_hash=session_user_id(recipient,self.salt) if recipient is not None else None,
            current_generation=scenario.get('generation',0),active_danger=ActiveRiskStore._view(risk,shop).active_danger,ask_after_hours=ask_after_hours)
        return ep,recipient,decision.reason

    def mark_prompt_sending(self,key:str,owner:str,*,now:datetime,ask_after_hours:float=6.)->dict:
        from datetime import timedelta
        self._clock(now);ref=self._ref('prompts',key)
        @firestore.transactional
        def mark(tx):
            row=self._read(ref,tx);_,recipient,reason=self._prompt_context(key,tx,now,ask_after_hours)
            if row.get('owner')!=owner or row.get('status')!='preparing' or row.get('lease_until',now)<=now:raise ValueError('Prompt lease unavailable')
            if reason!='due' or recipient is None or session_user_id(recipient,self.salt)!=row['owner_hash']:
                status='superseded' if reason in ('obsolete_scenario','already_answered','unavailable') else 'retryable'
                tx.set(ref,{**row,'status':status,'lease_until':now});return {'status':reason}
            tx.set(ref,{**row,'status':'sending','request_started_at':now,'lease_until':now+timedelta(seconds=30)})
            return {'status':'sending','recipient_chat_id':recipient}
        return mark(self.client.transaction(max_attempts=5))

    def finish_prompt(self,key:str,owner:str,*,now:datetime,status:str,message_id:int|None=None)->None:
        self._clock(now)
        if status not in ('accepted','simulated','uncertain','retryable'):raise ValueError('Invalid prompt outcome')
        if status=='accepted' and (type(message_id) is not int or message_id<=0):raise ValueError('Telegram acceptance requires message ID')
        if status!='accepted' and message_id is not None:raise ValueError('Only actual acceptance has message ID')
        ref=self._ref('prompts',key)
        @firestore.transactional
        def finish(tx):
            row=self._read(ref,tx)
            if row.get('owner')!=owner:raise ValueError('Prompt owner mismatch')
            if row.get('status') in ('accepted','simulated','uncertain'):
                if row['status']==status and row.get('message_id')==message_id:return
                raise ValueError('Terminal prompt outcome is immutable')
            if row.get('status')!='sending':raise ValueError('Prompt request was not started')
            if status=='simulated' and not row['is_demo']:raise ValueError('Real prompts cannot simulate delivery')
            tx.set(ref,{**row,'status':status,'message_id':message_id,'finished_at':now,'lease_until':now})
        finish(self.client.transaction(max_attempts=5))

    def pending(self,*,limit:int=20)->tuple[tuple[str,dict],...]:
        """Small recovery batches; overflow is unavailable, never partial success."""
        from google.cloud.firestore_v1.base_query import FieldFilter
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Invalid recovery batch')
        rows=list(self.client.collection(self.prefix+'outcome_prompts').where(filter=FieldFilter('status','in',['preparing','sending','retryable'])).limit(1001).stream(timeout=5,retry=None))
        if len(rows)>1000:raise ValueError('Pending outcome scan exceeds bound')
        return tuple((row.id,row.to_dict()) for row in rows[:limit])

    def episodes(self,*,is_demo:bool,generation:int|None)->tuple[OutcomeEpisode,...]:
        from google.cloud.firestore_v1.base_query import FieldFilter
        if type(is_demo) is not bool or is_demo!=(generation is not None) or (generation is not None and (type(generation) is not int or generation<0)):raise ValueError('Invalid episode realm')
        query=self.client.collection(self.prefix+'outcome_episodes').where(filter=FieldFilter('is_demo','==',is_demo))
        if is_demo:query=query.where(filter=FieldFilter('scenario_generation','==',generation))
        rows=list(query.limit(1001).stream(timeout=5,retry=None))
        if len(rows)>1000:raise ValueError('Episode scan exceeds bound')
        return tuple(OutcomeEpisode.model_validate_json(row.to_dict()['json']) for row in rows)

    def resolve_prompt_token(self,token:str,*,sender_chat_id:int,message_id:int,now:datetime)->str:
        self._clock(now)
        if type(token) is not str or len(token)!=32 or any(c not in '0123456789abcdef' for c in token) or type(sender_chat_id) is not int or type(message_id) is not int:raise ValueError('Invalid outcome callback')
        @firestore.transactional
        def resolve(tx):
            binding=self._read(self._ref('tokens',token),tx)
            if not binding or binding['owner_hash']!=session_user_id(sender_chat_id,self.salt):raise ValueError('Outcome callback owner mismatch')
            prompt=self._read(self._ref('prompts',binding['episode_key']),tx)
            if prompt.get('status')!='accepted' or prompt.get('message_id')!=message_id or prompt.get('callback_token')!=token:raise ValueError('Outcome callback requires accepted prompt')
            ep,recipient,reason=self._prompt_context(binding['episode_key'],tx,now,6.)
            if recipient!=sender_chat_id or (ep.is_demo,ep.scenario_generation)!=(binding['is_demo'],binding['scenario_generation']) or reason not in ('due','waiting','already_answered'):raise ValueError('Outcome callback unavailable')
            return binding['episode_key']
        return resolve(self.client.transaction(max_attempts=5))
