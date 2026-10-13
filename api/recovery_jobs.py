"""Protected, bounded manual recovery of three existing durable outboxes."""
import asyncio
from collections.abc import Callable,Awaitable
import time
from threading import Lock
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field
from api.config import Settings

class ResumeRequest(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    limit:int=Field(default=10,ge=1,le=20)

class StageOutcome(BaseModel):
    status:Literal['available','unavailable','deadline_limited']='available'
    scanned:int=0
    completed:int=0
    pending:int=0
    needs_review:int=0
    failed:int=0
    inflight_unknown:int=0

class ResumeResult(BaseModel):
    dispatch:StageOutcome
    confirmations:StageOutcome
    media_ledger:StageOutcome
    offline_cards:StageOutcome=Field(default_factory=StageOutcome)
    policy_deletions:StageOutcome=Field(default_factory=StageOutcome)
    note:str='Manual recovery only. An elapsed response deadline does not cancel an already-started external request; durable leases and logical identities govern retry.'

class RecoveryJobsService:
    def __init__(self,*,dispatch=None,confirmations=None,media=None,settings:Settings|None=None,client=None,deadline_seconds:float=30):
        if not 0<deadline_seconds<=45:raise ValueError('Recovery deadline must be positive and at most45 seconds')
        self.dispatch,self.confirmations,self.media=dispatch,confirmations,media
        self.settings,self.client,self.deadline_seconds=settings,client,deadline_seconds
        self.cards=None
        self.policy=None
        self.analytics=None
        self.analytics_lock=Lock()
        self.running:dict[str,asyncio.Task]={}

    def _analytics(self):
        with self.analytics_lock:
            if self.analytics is None:
                from api.tools.cloud_events import create_analytics_client
                self.analytics=create_analytics_client(self.settings)
            return self.analytics

    def _dispatch(self):
        if self.dispatch is None:
            from api.dispatch import create_dispatch_service
            self.dispatch=create_dispatch_service(self.settings)
        return self.dispatch

    def _confirmations(self):
        if self.confirmations is None:
            from api.vehicle_confirmations import VehicleConfirmationService,VehicleActionStore
            service=self
            class ConfirmationSink:
                def insert_confirmation(self,record):
                    from api.tools.cloud_events import GoogleEventSinks
                    # Confirmation rows use only analytics; no Pub/Sub client or
                    # separate stock scan is required for the shared collection.
                    GoogleEventSinks.insert_confirmation(self,record)
                def _insert(self,table,row,row_id):
                    client=service._analytics()
                    errors=client.insert_rows_json(f'{service.settings.gcp_project}.{service.settings.bigquery_dataset}.{table}',[row],row_ids=[row_id],timeout=10,retry=None)
                    if errors:raise RuntimeError('Confirmation analytics unavailable')
            self.confirmations=VehicleConfirmationService(VehicleActionStore(self.client),ConfirmationSink(),hash_salt=self.settings.hash_salt)
        return self.confirmations

    def _media(self):
        if self.media is None:
            from api.media import MediaService,EvidenceLedger
            from api.media_store import MediaStore
            self.media=MediaService(MediaStore(self.client,self.settings.hash_salt),None,None,EvidenceLedger(self._analytics(),self.settings.gcp_project,self.settings.bigquery_dataset),lambda request:False)
        return self.media

    async def _stage(self,name:str,scan:Callable[[],list[str]],work:Callable[[str],Awaitable[str]]) -> StageOutcome:
        prior=self.running.get(name)
        if prior and not prior.done():return StageOutcome(status='deadline_limited',inflight_unknown=1)
        result=StageOutcome();until=time.monotonic()+self.deadline_seconds
        async def run():
            try:ids=await asyncio.to_thread(scan)
            except Exception:
                result.status='unavailable';return result
            result.scanned=len(ids)
            for index,identity in enumerate(ids):
                if time.monotonic()>=until:
                    result.status='deadline_limited';result.pending+=len(ids)-index;break
                try:status=await work(identity)
                except Exception:result.failed+=1;result.pending+=1
                else:
                    if status=='complete':result.completed+=1
                    elif status=='needs_review':result.needs_review+=1
                    else:result.pending+=1
            return result
        task=asyncio.create_task(run());self.running[name]=task
        done,_=await asyncio.wait({task},timeout=self.deadline_seconds)
        if not done:
            # Retain the owned coroutine until its SDK operation actually finishes.
            # Do not close its client or admit another copy of this stage meanwhile.
            return StageOutcome(status='deadline_limited',scanned=result.scanned,completed=result.completed,pending=result.pending,failed=result.failed,needs_review=result.needs_review,inflight_unknown=1)
        return task.result()

    async def resume(self,limit:int=10) -> ResumeResult:
        if type(limit) is not int or not 1<=limit<=20:raise ValueError('Recovery batch must be1..20')
        async def dispatch(identity):
            service=await asyncio.to_thread(self._dispatch)
            result=await service.resume(identity)
            if result['status']=='superseded':
                event=await asyncio.to_thread(service.store.get_event,identity)
                return 'pending' if event['status']=='pending' else 'complete'
            return 'complete' if result['status']=='complete' else 'needs_review' if result['status']=='needs_review' else 'pending'
        async def confirmation(identity):
            service=await asyncio.to_thread(self._confirmations);await service.flush(identity)
            record=await asyncio.to_thread(lambda:service.store.client.collection(service.store.confirmations).document(identity).get(timeout=5,retry=None).to_dict())
            return 'complete' if record.get('bigquery')=='done' else 'pending'
        async def ledger(identity):
            service=await asyncio.to_thread(self._media)
            record=await service.resume_ledger(identity)
            return 'complete' if record.ledger_status=='done' else 'pending'
        async def card(identity):
            if self.cards is None:
                from api.offline_card_service import LazyOfflineCardService
                self.cards=LazyOfflineCardService(self.settings)
            status=await self.cards.deliver(identity)
            return 'complete' if status in ('accepted','superseded','virtual_skipped') else 'needs_review' if status=='uncertain' else 'pending'
        async def policy(identity):
            if self.policy is None:
                from api.policy import LazyPolicyService
                self.policy=LazyPolicyService(self.settings)
            service=await asyncio.to_thread(self.policy._service)
            await service._delete(await asyncio.to_thread(service.store.get,identity))
            job=await asyncio.to_thread(service.store.get,identity)
            return 'pending' if job['deletion_pending'] else 'complete'
        # Independent stages prevent a slow model/transport from starving evidence
        # or confirmed immutable facts. Each stage admits at most the bounded batch.
        outcomes=await asyncio.gather(
            self._stage('dispatch',lambda:self._dispatch_ids(limit),dispatch),
            self._stage('confirmations',lambda:self._confirmation_ids(limit),confirmation),
            self._stage('media_ledger',lambda:self._media_ids(limit),ledger),
            self._stage('offline_cards',lambda:self._card_ids(limit),card),
            self._stage('policy_deletions',lambda:self._policy_ids(limit),policy))
        return ResumeResult(dispatch=outcomes[0],confirmations=outcomes[1],media_ledger=outcomes[2],offline_cards=outcomes[3],policy_deletions=outcomes[4])

    def _dispatch_ids(self,limit):
        if self.dispatch is not None:return self.dispatch.store.pending_event_ids(limit)
        from api.dispatch_store import FirestoreDispatchStore
        return FirestoreDispatchStore(self.client).pending_event_ids(limit)
    def _confirmation_ids(self,limit):
        if self.confirmations is not None:return self.confirmations.store.pending_ids(limit)
        from api.vehicle_confirmations import VehicleActionStore
        return VehicleActionStore(self.client).pending_ids(limit)
    def _media_ids(self,limit):
        if self.media is not None:return self.media.store.pending_ledger_ids(limit)
        from api.media_store import MediaStore
        return MediaStore(self.client,self.settings.hash_salt).pending_ledger_ids(limit)

    def _card_ids(self,limit):
        if self.settings is None:return [] # Existing injected three-stage tests own no card runtime.
        from api.offline_card_store import FirestoreCardStore
        return FirestoreCardStore(self.client).pending_ids(limit)

    def _policy_ids(self,limit):
        if self.settings is None:return []
        from api.policy_store import PolicyStore
        return PolicyStore(self.client,self.settings.hash_salt).pending_deletions(limit)

    async def close(self):
        if self.running:await asyncio.gather(*self.running.values(),return_exceptions=True)
        if self.cards is not None:await self.cards.close()
        if self.policy is not None:await self.policy.close()
        if self.settings is not None:
            try:
                if self.dispatch is not None:await self.dispatch.close()
            finally:
                try:
                    if self.analytics is not None:await asyncio.to_thread(self.analytics.close)
                finally:
                    if self.client is not None:await asyncio.to_thread(self.client.close)


def create_recovery_jobs_service(settings:Settings) -> RecoveryJobsService:
    from api.tools.firestore import create_firestore_client
    if settings.scheduler_local_auth:
        import os
        from api.tools.emulators import loopback_endpoint
        for name,http in (('FIRESTORE_EMULATOR_HOST',False),('PUBSUB_EMULATOR_HOST',False),('BIGQUERY_EMULATOR_HOST',True)):
            loopback_endpoint(os.environ.get(name,''),http=http)
    return RecoveryJobsService(settings=settings,client=create_firestore_client(settings))
