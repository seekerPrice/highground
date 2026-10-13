"""Private immutable waste facts, owner consent and bounded synthetic projection."""
from datetime import UTC,datetime
from hashlib import sha256
import secrets
import re
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from api.photo_store import PhotoStore
from api.agents.sessions import session_user_id
from api.report_models import LossAssessment
from api.waste import aggregate_waste,donation_eligible,validate_waste
from api.waste_models import WasteRecord,WasteResponse
from api.demo_scenario import FIXTURE_ORIGIN,SHOP_IDS

class WasteDanger(ValueError):pass

class WasteStore(PhotoStore):
    def owner_shop(self,sender):
        shop=self.shop_for_sender(sender)
        return shop if shop and any(r.get('telegram_chat_id')==sender and r.get('role')=='owner' for r in shop['recipients']) else None

    def _guard(self,tx,shop_id,sender):
        shop=self.collection('shops').document(shop_id).get(transaction=tx).to_dict() or {}
        risk=self.client.collection(self.risk_store.risks).document(shop_id).get(transaction=tx).to_dict() or {}
        scenario=self.collection('demo_scenario').document('current').get(transaction=tx).to_dict() or {} if shop.get('is_demo') else {}
        if not any(r.get('telegram_chat_id')==sender and r.get('role')=='owner' for r in shop.get('recipients',[])):raise PermissionError('Owner required')
        if self.risk_store._view(risk,shop).active_danger:raise WasteDanger('Danger blocks property actions')
        if scenario.get('state')=='resetting':raise ValueError('Scenario reset is in progress')
        return dict(shop,scenario_generation=scenario.get('generation'))

    def stage_street(self,sender,label,operation):
        from api.waste_models import WasteRecord
        # Reuse the exact normalized rendering constraint without a guessed location.
        field=WasteRecord.model_fields['owner_confirmed_street']
        from pydantic import TypeAdapter
        from typing import Annotated
        label=label.strip()
        label=TypeAdapter(Annotated[str,field]).validate_python(label,strict=True)
        shop=self.owner_shop(sender)
        if not shop:raise PermissionError('Owner required')
        key=sha256(f'{shop["shop_id"]}:{session_user_id(sender,self.hash_salt)}:{operation}'.encode()).hexdigest()
        ref=self.collection('waste_street_intents').document(key);identity=secrets.token_hex(16)
        action=self.collection('waste_actions').document(identity)
        @firestore.transactional
        def stage(tx):
            guarded=self._guard(tx,shop['shop_id'],sender)
            prior=ref.get(transaction=tx).to_dict()
            if prior:return prior
            row=dict(action_id=identity,kind='street',shop_id=shop['shop_id'],sender_hash=session_user_id(sender,self.hash_salt),label=label,created_at=datetime.now(UTC),scenario_generation=guarded.get('scenario_generation'))
            tx.create(action,row);tx.create(ref,row)
            return row
        return stage(self.client.transaction())

    def action(self,identity,sender):
        ref=self.collection('waste_actions').document(identity)
        @firestore.transactional
        def read(tx):
            row=ref.get(transaction=tx).to_dict()
            if not row or row['sender_hash']!=session_user_id(sender,self.hash_salt):raise PermissionError('Owner required')
            shop=self._guard(tx,row['shop_id'],sender)
            if row.get('scenario_generation')!=shop.get('scenario_generation'):raise ValueError('Action belongs to an obsolete scenario')
            if row['kind']=='donation':self._eligible(tx,row,shop)
            return row
        return read(self.client.transaction())

    def _eligible(self,tx,row,shop):
        fact=self.collection('waste_assessments').document(row['report_id']).get(transaction=tx).to_dict()
        latest=self.collection('waste_current').document(row['shop_id']).get(transaction=tx).to_dict() or {}
        if not fact or latest.get('report_id')!=row['report_id'] or shop.get('baseline_inventory_id')!=row['inventory_id']:raise ValueError('Assessment is no longer current')
        assessment=WasteRecord.model_validate(fact).assessment
        item=next((i for i in assessment.items if i.item_id==row['item_id']),None)
        if item is None or not donation_eligible(item,owner_opt_in=True):raise ValueError('Item is not eligible')
        return item

    def confirm(self,identity,sender,*,available=True,operation=None):
        if type(available) is not bool:raise ValueError('Explicit availability required')
        ref=self.collection('waste_actions').document(identity)
        receipt=self.collection('waste_action_operations').document(sha256(f'{identity}:{operation}'.encode()).hexdigest()) if operation is not None else None
        @firestore.transactional
        def confirm(tx):
            row=ref.get(transaction=tx).to_dict()
            if not row or row['sender_hash']!=session_user_id(sender,self.hash_salt):raise PermissionError('Owner required')
            shop=self._guard(tx,row['shop_id'],sender)
            if row.get('scenario_generation')!=shop.get('scenario_generation'):raise ValueError('Action belongs to an obsolete scenario')
            if row['kind']=='donation':self._eligible(tx,row,shop)
            prior=receipt.get(transaction=tx).to_dict() if receipt else None
            if prior:return row
            if row['kind']=='street' and row.get('confirmed_at'):return row
            now=datetime.now(UTC)
            if row['kind']=='street':
                tx.update(self.collection('shops').document(row['shop_id']),{'owner_confirmed_street':row['label'],'street_confirmed_at':now,'street_assignment_source':'owner_confirmed_current_shop'})
                tx.update(ref,{'confirmed_at':now})
            else:tx.update(ref,{'available':available,'confirmed_at':now,'attribution':'explicit_owner_self_report'})
            if receipt:tx.create(receipt,{'action_id':identity,'confirmed_at':now,'available':available})
            return dict(row,available=available)
        return confirm(self.client.transaction())

    def report_context(self,job,bot_username):
        shop=self.collection('shops').document(job['shop_id']).get(timeout=5,retry=None).to_dict() or {}
        street=shop.get('owner_confirmed_street') if shop.get('street_assignment_source')=='owner_confirmed_current_shop' and shop.get('street_confirmed_at') else None
        result=dict(street=street,street_confirmed_at=shop.get('street_confirmed_at') if street else None,donations={})
        latest=self.collection('waste_current').document(job['shop_id']).get(timeout=5,retry=None).to_dict() or {}
        scenario=self.collection('demo_scenario').document('current').get(timeout=5,retry=None).to_dict() or {} if job['is_demo'] else {}
        current=latest.get('report_id')==job['report_id'] and shop.get('baseline_inventory_id')==job['baseline']['inventory_id'] and scenario.get('generation')==job.get('scenario_generation') and scenario.get('state','ready')=='ready'
        if not re.fullmatch(r'[A-Za-z0-9_]{5,32}',bot_username):bot_username=''
        for item_id,identity in job.get('donation_actions',{}).items():
            row=self.collection('waste_actions').document(identity).get(timeout=5,retry=None).to_dict() or {}
            if row.get('report_id')!=job['report_id'] or row.get('item_id')!=item_id:continue
            result['donations'][item_id]={'available':current and row.get('available') is True,'action_url':f'https://t.me/{bot_username}?start=donate_{identity}' if current and bot_username else None}
        return result

    def synthetic_scope(self):
        scenario=self.collection('demo_scenario').document('current').get(timeout=5,retry=None).to_dict() or {}
        if scenario.get('fixture_shop_ids') is not None:
            ids=scenario['fixture_shop_ids']
            if len(ids)>6 or len(set(ids))!=len(ids) or not set(ids).issubset(SHOP_IDS):raise ValueError('Unbounded fixture scope')
            rows=[]
            for identity in ids:
                shop=self.collection('shops').document(identity).get(timeout=5,retry=None).to_dict() or {}
                if shop.get('is_demo') is True and shop.get('fixture_origin')==FIXTURE_ORIGIN:rows.append(dict(shop,shop_id=identity))
            return rows
        docs=list(self.collection('shops').where(filter=FieldFilter('is_demo','==',True)).limit(51).stream(timeout=8,retry=None))
        if len(docs)>50:raise ValueError('Incomplete synthetic scope')
        return [dict(d.to_dict(),shop_id=d.id) for d in docs]

    def public(self,capacity):
        now=datetime.now(UTC);registered=None
        try:
            shops=self.synthetic_scope();registered=len(shops);scope={s['shop_id']:s for s in shops};records=[];scanned=0;unavailable_scopes=0
            scenario=self.collection('demo_scenario').document('current').get(timeout=5,retry=None).to_dict() or {}
            if scenario.get('state')=='resetting':raise ValueError('Scenario reset is in progress')
            # Scope-filter first so unrelated/private history cannot crowd out current facts.
            for identity,shop in scope.items():
                query=self.collection('waste_scopes').where(filter=FieldFilter('shop_id','==',identity)).where(filter=FieldFilter('is_demo','==',True))
                query=query.where(filter=FieldFilter('scenario_generation','==',scenario.get('generation')))
                docs=list(query.limit(1001).stream(timeout=8,retry=None))
                scanned+=len(docs)
                if scanned>1000:raise ValueError('Incomplete waste history')
                for doc in docs:
                    latest=doc.to_dict()
                    if latest.get('waste_status')!='available':unavailable_scopes+=1;continue
                    row=WasteRecord.model_validate(self.collection('waste_assessments').document(latest['report_id']).get(timeout=5,retry=None).to_dict())
                    if row.shop_id!=identity or row.assessment.inventory_id!=latest['inventory_id'] or row.episode_id!=latest['episode_id'] or not row.is_demo or row.scenario_generation!=latest.get('scenario_generation'):raise ValueError('Latest scope does not bind its immutable fact')
                    street=shop.get('owner_confirmed_street') if shop.get('street_assignment_source')=='owner_confirmed_current_shop' and shop.get('street_confirmed_at') else None
                    records.append(row.model_copy(update={'owner_confirmed_street':street}))
            assessed=len({r.shop_id for r in records if r.status=='complete'})
            return WasteResponse(status='available' if assessed else 'empty',generated_at=now,registered_synthetic_shops=registered,assessed_shops=assessed,missing_or_unavailable_shops=registered-assessed,aggregate=aggregate_waste(records,synthetic_shop_ids=set(scope),lorry_capacity_m3=capacity),note=f'Synthetic estimates only. {unavailable_scopes} latest completed episode/inventory scopes have unavailable waste quantities and are excluded from known totals. Shops without any available latest scope remain missing or unavailable. Street labels are current owner-confirmed values; load-equivalents do not promise collection.')
        except Exception:
            return WasteResponse(status='unavailable',generated_at=now,registered_synthetic_shops=registered,assessed_shops=None,missing_or_unavailable_shops=None,aggregate=None,note='Synthetic waste estimates are unavailable; this does not establish zero waste.')
