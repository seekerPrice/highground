"""Atomic source watermarks plus durable event/recovery intents."""
import asyncio
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import httpx
from google.cloud import firestore

from api.dispatch_models import EventRequest
from api.tools.datagov import EpisodeState, dedupe_warnings, fetch_warnings, DEFAULT_MAX_AGE


def source_episode(key, started):
    return sha256(f'{key}|{started.isoformat()}'.encode()).hexdigest()


class PollStore:
    def __init__(self,client,*,states='official_source_states',intents='official_poll_intents',status='official_source_status',max_age=DEFAULT_MAX_AGE):
        self.client,self.states,self.intents,self.status=client,states,intents,status
        self.recoveries=intents+'-recoveries'
        if not timedelta(0)<max_age<=DEFAULT_MAX_AGE:raise ValueError('Official cutoff must be positive and at most90 minutes')
        self.max_age=max_age

    def observe(self,result):
        self.client.collection(self.status).document(result.source).set(result.model_dump(mode='json',exclude={'warnings','resolved'}))
        # No absent/error/stale observation is interpreted as recovery.
        if result.status in ('current','degraded'):
            for key,at in result.resolved.items():self._transition(key,None,at,result.checked_at)
        for warning in result.warnings:
            if warning.geography.latitude is None or warning.geography.longitude is None:continue
            self._transition(f'{warning.source}:{warning.source_id}',warning,None,result.checked_at)

    def _transition(self,key,warning,resolved,checked_at):
        ref=self.client.collection(self.states).document(sha256(key.encode()).hexdigest())
        if resolved is not None and (resolved>checked_at or checked_at-resolved>self.max_age or datetime.now(UTC)-resolved>self.max_age):return
        @firestore.transactional
        def transition(tx):
            data=ref.get(transaction=tx).to_dict() or {}
            old=EpisodeState(**data['state']) if data.get('state') else None
            previous={key:old} if old else {}
            emitted,states=dedupe_warnings((warning,) if warning else (),previous,resolved={key:resolved} if resolved else {},episode_gap=timedelta(days=365000))
            if key not in states:return
            intents=[]
            recovery_episode=data.get('recovery_episode')
            if resolved is not None and old and resolved>=old.last_observed_at:
                if old.highest_level is not None:recovery_episode=source_episode(key,old.started_at)
            if resolved is not None and recovery_episode and old and resolved>=old.last_observed_at and (old.highest_level is not None or resolved>old.last_observed_at):
                episode=recovery_episode
                identity=sha256(f'recovery:{key}:{episode}:{resolved.isoformat()}'.encode()).hexdigest()
                intents.append((identity,{'kind':'recovery','source_key':key,'source_episode_id':episode,'observed_at':resolved,'status':'pending'}))
            for item in emitted:
                w=item.warning;episode=source_episode(key,states[key].started_at)
                request=EventRequest(request_id=item.event_id,source=w.source,level=w.level,lat=w.geography.latitude,lng=w.geography.longitude,
                                     reason=w.reason,source_key=key,source_episode_id=episode,source_observed_at=w.observed_at,
                                     source_valid_until=w.valid_until or w.observed_at+self.max_age)
                intents.append((item.event_id,{'kind':'event','request_json':request.model_dump_json(),'status':'pending'}))
            if emitted:recovery_episode=None
            # The watermark excludes exact retries, including completed NORMAL
            # intents; avoid additional conflicting reads inside the transaction.
            tx.set(ref,{'source_key':key,'state':asdict(states[key]),'checked_at':checked_at,'recovery_episode':recovery_episode})
            for identity,intent in intents:
                tx.set(self.client.collection(self.intents).document(identity),intent)
                if intent['kind']=='recovery':
                    receipt_id=sha256(f"{key}:{intent['source_episode_id']}".encode()).hexdigest()
                    tx.set(self.client.collection(self.recoveries).document(receipt_id),
                           {'source_key':key,'source_episode_id':intent['source_episode_id'],
                            'observed_at':resolved,'checked_at':checked_at,'accepted_max_age_seconds':int(self.max_age.total_seconds())})
        transition(self.client.transaction(max_attempts=10))

    def pending(self):
        from google.cloud.firestore_v1.base_query import FieldFilter
        return [(d.id,d.to_dict()) for d in self.client.collection(self.intents).where(filter=FieldFilter('status','==','pending')).stream()]

    def done(self,identity):self.client.collection(self.intents).document(identity).update({'status':'done'})


class PollService:
    def __init__(self,store,dispatch,risk,*,fetcher=fetch_warnings):self.store,self.dispatch,self.risk,self.fetcher=store,dispatch,risk,fetcher

    async def close(self):
        await self.dispatch.close()
        self.store.client.close()

    async def poll(self):
        async with httpx.AsyncClient(timeout=8) as client:
            results=await self.fetcher(client=client,max_age=self.store.max_age)
        for result in results:await asyncio.to_thread(self.store.observe,result)
        processed=0
        for identity,intent in await asyncio.to_thread(self.store.pending):
            if intent['kind']=='recovery':
                await asyncio.to_thread(self.risk.recover_official,intent['source_key'],intent['source_episode_id'],intent['observed_at'])
            else:
                request=EventRequest.model_validate_json(intent['request_json'])
                # Dispatch enforces original freshness again on recovery/restart.
                result=await self.dispatch.process(request)
                if result['status'] in ('busy','pending'):continue
            await asyncio.to_thread(self.store.done,identity);processed+=1
        return {'sources':{r.source:r.status for r in results},'processed_intents':processed}


def create_poll_service(settings):
    from api.dispatch import create_dispatch_service
    from api.tools.firestore import create_firestore_client
    from api.active_risk import ActiveRiskStore
    client=create_firestore_client(settings)
    return PollService(PollStore(client,max_age=settings.official_max_age),create_dispatch_service(settings),ActiveRiskStore(client,max_age=settings.official_max_age))
