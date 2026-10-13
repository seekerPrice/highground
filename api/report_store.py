"""Owner-only frozen recovery workflows and opaque capability-bound reports."""
from datetime import UTC, datetime
from hashlib import sha256
import hmac
import secrets
from google.cloud import firestore
from api.inventory_store import InventoryStore
from api.agents.sessions import session_user_id
from api.report_models import freeze_baseline
from api.media_models import MediaIngestError

class ReportStore(InventoryStore):
    def owner_shop(self, sender: int) -> dict | None:
        shop=self.shop_for_sender(sender)
        if shop and any(r.get('telegram_chat_id')==sender and r.get('role')=='owner' for r in shop['recipients']): return shop
        return None

    def current(self, sender: int) -> dict | None:
        identity=session_user_id(sender,self.hash_salt)
        pointer=self.collection('recovery_current').document(identity).get().to_dict() or {}
        return self.collection('recovery_jobs').document(pointer['report_id']).get().to_dict() if pointer.get('report_id') else None

    def upload_reference(self,sender: int,message_id: int,file_unique_id: str):
        identity=sha256(f"{session_user_id(sender,self.hash_salt)}:{message_id}:{file_unique_id}".encode()).hexdigest()
        return self.collection('recovery_uploads').document(identity)

    def resolve_context(self,sender: int,message_id: int|None=None,file_unique_id: str|None=None) -> dict|None:
        if message_id is not None and file_unique_id:
            bound=self.upload_reference(sender,message_id,file_unique_id).get().to_dict() or {}
            if bound.get('report_id'):
                job=self.collection('recovery_jobs').document(bound['report_id']).get().to_dict()
                return dict(job,bound_upload=True) if job else None
        job=self.current(sender)
        return job if job and (job['status']!='complete' or job.get('attachment_pending')) else None

    def bind_photo(self,report_id: str,sender: int,message_id: int,file_unique_id: str) -> dict:
        ref=self.collection('recovery_jobs').document(report_id);binding=self.upload_reference(sender,message_id,file_unique_id)
        @firestore.transactional
        def bind(tx):
            old=binding.get(transaction=tx).to_dict()
            job=ref.get(transaction=tx).to_dict()
            if old:
                if old['report_id']!=report_id or old['kind']!='waterline_photo':raise MediaIngestError('recovery_upload_bound')
                return job
            if job['sender_hash']!=session_user_id(sender,self.hash_salt):raise MediaIngestError('unauthorized_media')
            tx.create(binding,{'report_id':report_id,'kind':'waterline_photo'})
            return job
        return bind(self.client.transaction())

    def start(self, shop: dict, sender: int, operation: str) -> dict:
        identity=sha256(f"{shop['shop_id']}:{session_user_id(sender,self.hash_salt)}:{operation}".encode()).hexdigest()
        intent=self.collection('recovery_intents').document(identity)
        current=self.collection('recovery_current').document(session_user_id(sender,self.hash_salt))
        report_id=secrets.token_hex(16); token=secrets.token_urlsafe(32)
        ref=self.collection('recovery_jobs').document(report_id)
        private=self.collection('recovery_private').document(report_id)
        baseline_ref=self.collection('inventories').document(shop.get('baseline_inventory_id') or 'unavailable')
        @firestore.transactional
        def create(tx):
            old=intent.get(transaction=tx).to_dict()
            if old:return self.collection('recovery_jobs').document(old['report_id']).get(transaction=tx).to_dict()
            prior=current.get(transaction=tx).to_dict() or {}
            prior_job=self.collection('recovery_jobs').document(prior['report_id']).get(transaction=tx).to_dict() if prior.get('report_id') else None
            baseline=baseline_ref.get(transaction=tx).to_dict()
            risk=self.client.collection(self.risk_store.risks).document(shop['shop_id']).get(transaction=tx).to_dict() or {}
            scenario=self.collection('demo_scenario').document('current').get(transaction=tx).to_dict() or {} if shop.get('is_demo') else {}
            if prior_job and prior_job.get('status') in ('awaiting_declaration','awaiting_video'): return prior_job
            if not baseline or baseline.get('shop_id')!=shop['shop_id']:raise ValueError('Baseline unavailable')
            frozen=freeze_baseline(dict(baseline,inventory_id=baseline_ref.id))
            if scenario.get('state')=='resetting':raise ValueError('Scenario reset is in progress')
            episode=self.risk_store._view(risk,shop).episode_id
            record=dict(report_id=report_id,inventory_id=report_id,shop_id=shop['shop_id'],shop_name=shop.get('shop_name','Shop'),
                language=shop['language'],is_demo=bool(shop.get('is_demo')),sender_hash=session_user_id(sender,self.hash_salt),
                created_at=datetime.now(UTC),status='awaiting_declaration',baseline=frozen,lat=shop['lat'],lng=shop['lng'],
                capability_hash=sha256(token.encode()).hexdigest(),evidence_media_ids=[frozen['media_id']],
                waste_episode_id=episode or sha256(f"unattributed:{shop['shop_id']}:{frozen['inventory_id']}".encode()).hexdigest(),
                waste_episode_attribution='persisted_flood_episode' if episode else 'unattributed_shop_inventory_scope',
                scenario_generation=scenario.get('generation'))
            tx.create(ref,record);tx.create(private,{'capability':token});tx.create(intent,{'report_id':report_id});tx.set(current,{'report_id':report_id})
            return record
        return create(self.client.transaction())

    def complete_assessment(self,report_id,owner,assessment):
        """Commit the original loss and independent waste projection atomically."""
        from api.report_models import LossAssessment
        from api.waste_models import WasteRecord
        from api.waste import validate_waste,donation_eligible
        ref=self.collection('recovery_jobs').document(report_id)
        tokens={item.item_id:secrets.token_hex(16) for item in assessment.waste.items} if assessment.waste else {}
        @firestore.transactional
        def complete(tx):
            job=ref.get(transaction=tx).to_dict()
            if job.get('owner')!=owner:raise MediaIngestError('inventory_claim_changed')
            if job.get('status')=='complete':return job
            assessment.validate_baseline(job['baseline'],job['upload']['duration'])
            if job.get('assessment') and LossAssessment.model_validate(job['assessment'])!=assessment:raise MediaIngestError('metadata_conflict')
            validated=assessment.model_copy(update={'waste':validate_waste(assessment.waste,job['baseline'],assessment,job['media_id'],job['upload']['duration'])}) if assessment.waste else assessment
            now=datetime.now(UTC);shop=self.collection('shops').document(job['shop_id']).get(transaction=tx).to_dict() or {}
            scenario=self.collection('demo_scenario').document('current').get(transaction=tx).to_dict() or {} if job['is_demo'] else {}
            current_ref=self.collection('waste_current').document(job['shop_id']);current=current_ref.get(transaction=tx).to_dict() or {}
            generation_current=not job['is_demo'] or (scenario.get('generation')==job.get('scenario_generation') and scenario.get('state','ready')=='ready')
            actions={item.item_id:tokens[item.item_id] for item in validated.waste.items if donation_eligible(item,owner_opt_in=True)} if validated.waste and generation_current and shop.get('baseline_inventory_id')==job['baseline']['inventory_id'] else {}
            values=dict(status='complete',assessment=validated.model_dump(),completed_at=now,donation_actions=actions)
            episode_id=job.get('waste_episode_id') or sha256(f"unattributed:{job['shop_id']}:{job['baseline']['inventory_id']}".encode()).hexdigest()
            scope_id=sha256(f"{job['shop_id']}:{episode_id}:{job['baseline']['inventory_id']}".encode()).hexdigest()
            scope_ref=self.collection('waste_scopes').document(scope_id)
            scope=scope_ref.get(transaction=tx).to_dict() or {}
            if generation_current:
                if not current.get('completed_at') or now>=current['completed_at']:tx.set(current_ref,{'report_id':report_id,'completed_at':now})
                if not scope.get('completed_at') or now>=scope['completed_at']:tx.set(scope_ref,{'report_id':report_id,'shop_id':job['shop_id'],'inventory_id':job['baseline']['inventory_id'],'episode_id':episode_id,'waste_status':validated.waste_status,'completed_at':now,'is_demo':job['is_demo'],'scenario_generation':job.get('scenario_generation')})
            if validated.waste is not None:
                street=shop.get('owner_confirmed_street') if shop.get('street_assignment_source')=='owner_confirmed_current_shop' and shop.get('street_confirmed_at') else None
                fact=WasteRecord(assessment_id=report_id,shop_id=job['shop_id'],episode_id=job.get('waste_episode_id') or sha256(f"unattributed:{job['shop_id']}:{job['baseline']['inventory_id']}".encode()).hexdigest(),completed_at=now,status='complete',is_demo=job['is_demo'],owner_confirmed_street=street,baseline_items=len(job['baseline']['items']),assessment=validated.waste,scenario_generation=job.get('scenario_generation'))
                tx.create(self.collection('waste_assessments').document(report_id),fact.model_dump())
                for item_id,identity in actions.items():
                    index=int(item_id.rsplit(':',1)[1])
                    tx.create(self.collection('waste_actions').document(identity),dict(action_id=identity,kind='donation',shop_id=job['shop_id'],sender_hash=job['sender_hash'],report_id=report_id,item_id=item_id,item_name=job['baseline']['items'][index]['name'],inventory_id=job['baseline']['inventory_id'],scenario_generation=job.get('scenario_generation'),available=False,created_at=now))
            tx.update(ref,values)
            return dict(job,**values)
        return complete(self.client.transaction())

    def waste_context(self,job):
        from api.waste_store import WasteStore
        return WasteStore(self.client,self.hash_salt,self.prefix,risks=self.risk_store).report_context(job,getattr(self,'bot_username',''))

    def declare(self, report_id: str, sender: int) -> dict:
        ref=self.collection('recovery_jobs').document(report_id)
        job=ref.get().to_dict(); shop=self.owner_shop(sender)
        if not job or not shop or shop['shop_id']!=job['shop_id'] or job['sender_hash']!=session_user_id(sender,self.hash_salt): raise MediaIngestError('unauthorized_media')
        state=self.risk_store.get(shop['shop_id'])
        if state.official_danger or state.legacy_unknown:return job
        if not shop.get('is_demo'): self.risk_store.owner_declared_recovery(shop['shop_id'],sender)
        if self.danger_active(shop['shop_id']):return job
        @firestore.transactional
        def transition(tx):
            current=ref.get(transaction=tx).to_dict()
            if current['status']=='awaiting_declaration':
                tx.update(ref,{'status':'awaiting_video','recovery_attribution':'Owner declared recovery; not independent proof of flood clearance.','declared_at':datetime.now(UTC)})
            return dict(current,status='awaiting_video') if current['status']=='awaiting_declaration' else current
        return transition(self.client.transaction())

    def exit(self,sender):
        self.collection('recovery_current').document(session_user_id(sender,self.hash_salt)).delete()

    def request_attachment(self,sender):
        job=self.current(sender);shop=self.owner_shop(sender)
        if not job or not shop or job['status']!='complete':return None
        self.collection('recovery_jobs').document(job['report_id']).update({'attachment_pending':True})
        return job

    def bind_upload(self, report_id: str, sender: int, message_id: int, sent: datetime, video, now: datetime, *, receipt_only: bool=False) -> dict:
        """Freeze a media receipt before selecting any assessment input."""
        ref=self.collection('recovery_jobs').document(report_id)
        binding=self.upload_reference(sender,message_id,video.file_unique_id)
        @firestore.transactional
        def bind(tx):
            prior=binding.get(transaction=tx).to_dict();job=ref.get(transaction=tx).to_dict()
            if prior and (prior['report_id']!=report_id or prior['kind']!='after_video'):raise MediaIngestError('recovery_upload_bound')
            if job['sender_hash']!=session_user_id(sender,self.hash_salt):raise MediaIngestError('unauthorized_media')
            if prior:
                upload=prior.get('upload') or job.get('upload')
                if not upload:raise MediaIngestError('recovery_upload_unavailable')
                return dict(job,received_upload=upload,receipt_only=prior.get('receipt_only',False))
            upload=dict(message_id=message_id,telegram_date=sent,received_at=now,duration=video.duration,file_unique_id=video.file_unique_id)
            only=receipt_only or job['status']=='awaiting_declaration'
            tx.create(binding,{'report_id':report_id,'kind':'after_video','upload':upload,'receipt_only':only})
            return dict(job,received_upload=upload,receipt_only=only)
        return bind(self.client.transaction())

    def select_upload(self,report_id: str,owner: str,sender: int,message_id: int,file_unique_id: str,media_id: str) -> dict|None:
        """Only an eligible, declared clip becomes the report's assessment input."""
        ref=self.collection('recovery_jobs').document(report_id);binding=self.upload_reference(sender,message_id,file_unique_id)
        @firestore.transactional
        def select(tx):
            job=ref.get(transaction=tx).to_dict();upload=binding.get(transaction=tx).to_dict()
            risk=self.client.collection(self.risk_store.risks).document(job['shop_id']).get(transaction=tx).to_dict() or {}
            shop=self.collection('shops').document(job['shop_id']).get(transaction=tx).to_dict() or {}
            if job.get('owner')!=owner:raise MediaIngestError('inventory_claim_changed')
            if not upload or upload['report_id']!=report_id or upload['kind']!='after_video':raise MediaIngestError('recovery_upload_bound')
            if upload.get('receipt_only') or job['status']=='awaiting_declaration':return None
            if self.risk_store._view(risk,shop).active_danger:
                if not job.get('assessment'):tx.update(binding,{'receipt_only':True})
                return None
            selected=upload.get('upload') or job.get('upload')
            if not selected:raise MediaIngestError('recovery_upload_unavailable')
            if job.get('upload'):
                if (job['upload']['message_id'],job['upload']['file_unique_id'])!=(message_id,file_unique_id):raise MediaIngestError('recovery_upload_bound')
                return job
            tx.update(ref,{'upload':selected,'media_id':media_id})
            return dict(job,upload=selected,media_id=media_id)
        return select(self.client.transaction())

    def preserve_receipt_only(self,report_id: str,owner: str,sender: int,message_id: int,file_unique_id: str) -> None:
        """Release this unassessed selection; original receipt facts stay frozen."""
        ref=self.collection('recovery_jobs').document(report_id);binding=self.upload_reference(sender,message_id,file_unique_id)
        @firestore.transactional
        def release(tx):
            job=ref.get(transaction=tx).to_dict();upload=binding.get(transaction=tx).to_dict()
            if job.get('owner')!=owner:raise MediaIngestError('inventory_claim_changed')
            if not upload or upload['report_id']!=report_id or upload['kind']!='after_video':raise MediaIngestError('recovery_upload_bound')
            if job.get('assessment'):return
            tx.update(binding,{'receipt_only':True})
            selected=job.get('upload')
            if selected and (selected['message_id'],selected['file_unique_id'])==(message_id,file_unique_id):
                tx.update(ref,{'upload':firestore.DELETE_FIELD,'media_id':firestore.DELETE_FIELD,'status':'awaiting_video'})
        release(self.client.transaction())

    # InventoryStore's bounded transaction lease methods operate on the recovery job collection.
    def collection(self, name):
        return super().collection('recovery_jobs' if name=='inventory_jobs' else name)

    def authorized(self, report_id: str, token: str) -> dict | None:
        job=self.collection('recovery_jobs').document(report_id).get().to_dict() or {}
        supplied=sha256(token.encode()).hexdigest()
        if not hmac.compare_digest(supplied,job.get('capability_hash','0'*64)):return None
        return job if job.get('status')=='complete' else None

    def token(self, report_id: str) -> str:
        return self.collection('recovery_private').document(report_id).get().to_dict()['capability']

    def attach_photo(self, report_id: str, media_id: str) -> None:
        ref=self.collection('recovery_jobs').document(report_id)
        @firestore.transactional
        def attach(tx):
            job=ref.get(transaction=tx).to_dict()
            values=job['evidence_media_ids']
            if media_id not in values:
                if len(values)>=10:raise ValueError('Evidence limit reached')
                tx.update(ref,{'evidence_media_ids':values+[media_id]})
        attach(self.client.transaction())
