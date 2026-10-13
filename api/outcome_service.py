"""Manual, bounded owner outcome collection; delivery acceptance is not reading."""
import asyncio
import time
from datetime import UTC,datetime
from typing import Callable,Protocol
from api.active_risk import ActiveRiskStore
from api.photo_store import PhotoStore
from api.outcome_store import FirestoreOutcomeStore
from api.outcome_history import OutcomeHistoryAdapter
from api.outcome_models import OwnerOutcome,OutcomeEpisode
from api.tools.telegram import TelegramAPI
from api.reply_guard import ReplyGuard,Shop
from api.destinations import DestinationLookup
from api.config import Settings
from api.inventory_models import InventoryReply
from api.i18n import text,catalog
from api.outcome_models import CalibrationState
from api.tools.telegram import TelegramSendError


class OutcomeSink(Protocol):
    def insert_outcome(self,response:OwnerOutcome,episode:OutcomeEpisode)->None: ...
    def close(self)->None: ...

class OutcomeReply(InventoryReply):
    owner_required:bool=False


class OutcomeService:
    def __init__(self,outcome_store:FirestoreOutcomeStore,history:OutcomeHistoryAdapter,telegram:TelegramAPI,sinks:OutcomeSink,*,risk_store:ActiveRiskStore,shop_store:PhotoStore,ask_after_hours:float=6.,clock:Callable[[],datetime]=lambda:datetime.now(UTC),max_job_seconds:float=25.,destinations:DestinationLookup|None=None,owns_clients:bool=False)->None:
        if not 0<ask_after_hours<=720 or not 0<max_job_seconds<=25:raise ValueError('Outcome budgets must be bounded')
        self.store=shop_store;self.guard=ReplyGuard(shop_store,destinations=destinations)
        self.outcomes,self.history,self.telegram,self.sinks=outcome_store,history,telegram,sinks
        self.risks,self.ask_after_hours,self.clock,self.max_job_seconds=risk_store,ask_after_hours,clock,max_job_seconds
        self.owns_clients=owns_clients;self.running=None

    async def danger_reply(self,shop:Shop)->InventoryReply:
        return await self.guard.danger_reply(shop)

    async def reply(self,shop:Shop|None,key:str)->InventoryReply:
        return await self.guard.reply(shop,key)

    async def answer(self,sender:int,token:str,message_id:int,answer:str)->InventoryReply:
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender)
        if shop and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        try:
            key=await asyncio.to_thread(self.outcomes.resolve_prompt_token,token,sender_chat_id=sender,message_id=message_id,now=self.clock())
            episode=await asyncio.to_thread(self.outcomes.episode,key)
            # This is explicitly an episode reference, never a claimed observation.
            reference=episode.closed_at or episode.started_at
            await asyncio.to_thread(self.outcomes.record_response,key,sender_chat_id=sender,answer=answer,observed_at=reference,now=self.clock())
        except ValueError:return await self.reply(shop,'outcome_unavailable')
        return await self.reply(shop,'outcome_recorded')

    async def owner_report(self,sender:int,declared_time:str|None,depth_cm:int|None=None)->InventoryReply:
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender)
        if shop and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        try:
            if not shop or not any(r.get('role')=='owner' and r.get('telegram_chat_id')==sender for r in shop.get('recipients',[])):raise ValueError()
            if not declared_time:
                reply=await self.reply(shop,'outcome_inside_instructions')
                return OutcomeReply(**reply.model_dump(),owner_required=True)
            if depth_cm is not None and (type(depth_cm) is not int or not 0<=depth_cm<=1000):raise ValueError()
            observed=datetime.fromisoformat(declared_time.replace('Z','+00:00'))
            if observed.tzinfo is None or observed>self.clock():raise ValueError()
            from api.demo_scenario import current_scenario,scenario_collection
            scenario=await asyncio.to_thread(current_scenario,self.outcomes.client,scenario_collection(self.outcomes.shops)) if shop.get('is_demo') else {}
            episodes=await asyncio.to_thread(self.outcomes.episodes,is_demo=bool(shop.get('is_demo')),generation=scenario.get('generation',0) if shop.get('is_demo') else None)
            matched=[ep for ep in episodes if ep.shop_id==shop['shop_id'] and ep.started_at<=observed and (ep.closed_at is None or observed<=ep.closed_at)]
            if len(matched)!=1:raise ValueError()
            from api.outcome_store import episode_key
            await asyncio.to_thread(self.outcomes.record_response,episode_key(matched[0]),sender_chat_id=sender,answer='inside',observed_at=observed,now=self.clock(),entrypoint='owner_report',depth_cm=depth_cm)
        except ValueError:return await self.reply(shop,'outcome_unavailable')
        return await self.reply(shop,'outcome_recorded')

    async def _prompt(self,key:str,deadline:float|None=None)->str:
        async def call(function,*args,**kwargs):
            self.history._deadline(deadline)
            return await asyncio.to_thread(function,*args,**kwargs)
        row=await call(self.outcomes.claim_prompt,key,now=self.clock(),ask_after_hours=self.ask_after_hours)
        if row['status']!='preparing':return 'already_accepted' if row['status']=='accepted' else row['status']
        owner=row['owner'];episode=await call(self.outcomes.episode,key)
        sending=await call(self.outcomes.mark_prompt_sending,key,owner,now=self.clock(),ask_after_hours=self.ask_after_hours)
        if sending['status']!='sending':return sending['status']
        lease=None;transport_started=False
        try:
            status,lease=await call(self.risks.claim_outcome_delivery,episode,sending['recipient_chat_id'])
            if status!='claimed':
                await asyncio.to_thread(self.outcomes.finish_prompt,key,owner,now=self.clock(),status='retryable')
                return status
            shop=await call(self.store.shop_for_sender,sending['recipient_chat_id'])
            language=shop.get('language','en') if shop else 'en'
            # All text is static/localized. No property/media prompt at Danger.
            markup={'inline_keyboard':[[{'text':text(language,'outcome_'+label+'_button'),'callback_data':f"outcome:{row['callback_token']}:{label}"} for label in ('no','street')],
                                       [{'text':text(language,'outcome_'+label+'_button'),'callback_data':f"outcome:{row['callback_token']}:{label}"} for label in ('entrance','inside')]]}
            reference=text(language,'outcome_episode_closed',start=episode.started_at.astimezone(UTC).isoformat(),end=episode.closed_at.astimezone(UTC).isoformat()) if episode.closed_at else text(language,'outcome_episode_open',start=episode.started_at.astimezone(UTC).isoformat())
            pieces=([text(language,'simulation_label')] if episode.is_demo else [])+[reference,text(language,'outcome_prompt')]
            if not catalog(language)['_reviewed']:pieces.append(text(language,'translation_notice'))
            rendered='\n'.join(pieces)
            if len(rendered)>4096:raise ValueError('Outcome prompt exceeds limit')
            final,checked=await call(self.risks.claim_outcome_delivery,episode,sending['recipient_chat_id'],owner=lease)
            if final!='claimed':
                await asyncio.to_thread(self.outcomes.finish_prompt,key,owner,now=self.clock(),status='retryable')
                return final
            transport_started=True
            try:message_id=await call(self.telegram.send_message,sending['recipient_chat_id'],rendered,markup)
            except TelegramSendError as error:
                await asyncio.to_thread(self.outcomes.finish_prompt,key,owner,now=self.clock(),status='uncertain' if error.uncertain else 'retryable')
                return 'uncertain' if error.uncertain else 'retryable'
            except Exception:
                await asyncio.to_thread(self.outcomes.finish_prompt,key,owner,now=self.clock(),status='uncertain')
                return 'uncertain'
            await asyncio.to_thread(self.outcomes.finish_prompt,key,owner,now=self.clock(),status='accepted',message_id=message_id)
            return 'accepted'
        except Exception:
            if not transport_started:
                await asyncio.to_thread(self.outcomes.finish_prompt,key,owner,now=self.clock(),status='retryable')
            # After transport starts, an uncommitted acceptance remains ambiguous.
            raise
        finally:
            if lease:await asyncio.to_thread(self.risks.release_delivery,episode.shop_id,lease)

    async def _flush(self,key:str,deadline:float|None=None)->str:
        async def call(function,*args,**kwargs):
            self.history._deadline(deadline)
            return await asyncio.to_thread(function,*args,**kwargs)
        response=await call(self.outcomes.pending_fact,key)
        if response is None:return 'complete'
        episode=await call(self.outcomes.episode,key)
        if episode is None:raise ValueError('Confirmed episode unavailable')
        await call(self.sinks.insert_outcome,response,episode)
        await call(self.outcomes.acknowledge_fact,key,response)
        return 'complete'

    def _pending_facts(self,limit:int)->tuple[str,...]:
        return self.outcomes.pending_fact_keys(limit)

    async def ask(self,limit:int=20)->dict[str,str|int]:
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Invalid outcome work budget')
        if self.running and not self.running.done():return {'status':'deadline_limited','inflight_unknown':1}
        deadline=time.monotonic()+self.max_job_seconds
        async def run():
            result={'status':'available','prompts_accepted':0,'pending':0,'failed':0,'outcomes_completed':0,'calibration_overflow_areas':0,'calibration_changes':0}
            keys=await asyncio.to_thread(self.history.refresh,limit=limit,now=self.clock(),deadline=deadline)
            if time.monotonic()>=deadline:return {**result,'status':'deadline_limited'}
            pending=await asyncio.to_thread(self.outcomes.pending,limit=limit)
            identities=tuple(dict.fromkeys([key for key,_ in pending]+list(keys)))[:limit]
            for index,key in enumerate(identities):
                if time.monotonic()>=deadline:result['status']='deadline_limited';result['pending']+=len(identities)-index;break
                try:status=await self._prompt(key,deadline)
                except Exception:result['failed']+=1;continue
                if status=='accepted':result['prompts_accepted']+=1
                elif status not in ('simulated','already_answered','already_accepted','uncertain','superseded'):result['pending']+=1
            if time.monotonic()>=deadline:return {**result,'status':'deadline_limited'}
            facts=await asyncio.to_thread(self._pending_facts,limit)
            for fact in facts:
                if time.monotonic()>=deadline:result['status']='deadline_limited';break
                try:await self._flush(fact,deadline);result['outcomes_completed']+=1
                except Exception:result['failed']+=1
            if time.monotonic()<deadline:
                batches,overflow=await asyncio.to_thread(self.history.calibration_batches,now=self.clock(),deadline=deadline)
                result['calibration_overflow_areas']=len(overflow)
                for (area,demo,generation),evidence in batches.items():
                    if time.monotonic()>=deadline:result['status']='deadline_limited';break
                    state=await asyncio.to_thread(self.outcomes.calibration_state,area,is_demo=demo,generation=generation)
                    if state is None:state=CalibrationState(area=area,is_demo=demo,scenario_generation=generation)
                    try:decision=await asyncio.to_thread(self.outcomes.calibrate,state,evidence,now=self.clock(),deadline=deadline)
                    except Exception:result['failed']+=1
                    else:result['calibration_changes']+=int(decision.new_multiplier!=decision.old_multiplier)
            return result
        self.running=asyncio.create_task(run())
        # The response deadline can precede the retained task's completion.
        # Retrieve every eventual exception even when a later job replaces it.
        self.running.add_done_callback(lambda task:task.exception() if not task.cancelled() else None)
        done,_=await asyncio.wait({self.running},timeout=self.max_job_seconds)
        if not done:return {'status':'deadline_limited','inflight_unknown':1}
        return self.running.result()

    async def recheck_reply(self,sender:int,reply:InventoryReply)->InventoryReply:
        guarded=await self.guard.recheck_reply(sender,reply)
        if guarded.kind=='danger':return guarded
        if getattr(reply,'owner_required',False):
            shop=await asyncio.to_thread(self.store.shop_for_sender,sender)
            if not shop or not any(r.get('role')=='owner' and r.get('telegram_chat_id')==sender for r in shop.get('recipients',[])):return await self.reply(shop,'outcome_unavailable')
        return guarded

    async def close(self)->None:
        if self.running:await asyncio.gather(self.running,return_exceptions=True)
        if self.owns_clients:
            if self.telegram is not None and hasattr(self.telegram,'close'):self.telegram.close()
            self.sinks.close();self.outcomes.client.close()


def create_outcome_service(settings:Settings)->OutcomeService:
    from api.tools.firestore import create_firestore_client
    from api.photo_store import PhotoStore
    from api.active_risk import ActiveRiskStore
    from api.outcome_store import FirestoreOutcomeStore
    from api.outcome_history import OutcomeHistoryAdapter
    from api.tools.telegram import TelegramAPI
    from api.destinations import DestinationLookup
    client=create_firestore_client(settings)
    risks=ActiveRiskStore(client,max_age=settings.official_max_age,episode_history='risk_episode_history')
    store=FirestoreOutcomeStore(client,settings.hash_salt)
    class LazySink:
        active=None
        def insert_outcome(self,response:OwnerOutcome,episode:OutcomeEpisode)->None:
            if self.active is None:
                from api.tools.cloud_events import create_analytics_client
                from api.outcome_analytics import OutcomeAnalytics
                import os
                self.active=OutcomeAnalytics(create_analytics_client(settings),settings.gcp_project,settings.bigquery_dataset,store,emulator_host=os.environ.get('BIGQUERY_EMULATOR_HOST') or None)
            self.active.insert_outcome(response,episode)
        def close(self)->None:
            if self.active:self.active.close()
    return OutcomeService(store,OutcomeHistoryAdapter(client,store,risks),TelegramAPI(settings.telegram_bot_token),LazySink(),risk_store=risks,
        shop_store=PhotoStore(client,settings.hash_salt,risks=risks),ask_after_hours=settings.outcome_ask_after_h,
        destinations=DestinationLookup(client,radius_m=settings.destination_search_radius_m),owns_clients=True)

class LazyOutcomeService:
    def __init__(self,settings:Settings)->None:self.settings=settings;self.active=None
    def _service(self)->OutcomeService:
        if self.active is None:self.active=create_outcome_service(self.settings)
        return self.active
    async def owner_report(self,sender:int,declared_time:str|None,depth_cm:int|None=None)->InventoryReply:return await self._service().owner_report(sender,declared_time,depth_cm)
    async def answer(self,sender:int,token:str,message_id:int,answer:str)->InventoryReply:return await self._service().answer(sender,token,message_id,answer)
    async def recheck_reply(self,sender:int,reply:InventoryReply)->InventoryReply:return await self._service().recheck_reply(sender,reply)
    async def close(self)->None:
        if self.active:await self.active.close()
