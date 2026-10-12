"""Accepted-message-bound immutable stock actions and recoverable confirmation outbox."""
from datetime import datetime
from hashlib import sha256
from google.cloud import firestore
from api.dispatch_models import ActionSnapshot,Shop
from api.agents.sessions import session_user_id
from api.vehicle_confirmations import VehicleActionStore,VehicleConfirmationService,ConfirmationStatus
from api.active_risk import ActiveRiskStore

class StockActionStore(VehicleActionStore):
    def __init__(self,client:firestore.Client,*,actions:str='stock_actions',confirmations:str='confirmations',
                 alerts:str='alerts',shops:str='shops',risks:str='active_risks'):
        super().__init__(client,actions=actions,confirmations=confirmations,alerts=alerts,shops=shops)
        self.risks=risks

    def prepare(self,event:dict,shop:Shop,snapshot:ActionSnapshot,hash_salt:str)->dict:
        identity=sha256(f"{event['event_id']}:{shop.shop_id}:stock".encode()).hexdigest()[:32]
        ref=self.client.collection(self.actions).document(identity)
        frozen=snapshot.model_copy(update={'stock_action_id':identity,'episode_id':event.get('episode_id') or event['event_id']})
        record=dict(action_id=identity,event_id=event['event_id'],shop_id=shop.shop_id,episode_id=frozen.episode_id,
            kind='stock',snapshot=frozen.model_dump(mode='json'),state='active',is_demo=event['is_demo'],
            recipient_hashes=[session_user_id(r.telegram_chat_id,hash_salt) for r in shop.recipients],created_at=event['created_at'])
        @firestore.transactional
        def save(tx):
            existing=ref.get(transaction=tx)
            shop_data=self.client.collection(self.shops).document(shop.shop_id).get(transaction=tx).to_dict() or {}
            risk=self.client.collection(self.risks).document(shop.shop_id).get(transaction=tx).to_dict() or {}
            state=ActiveRiskStore._view(risk,shop_data)
            record['danger_generation']=risk.get('danger_generation',0)
            if existing.exists:return existing.to_dict()
            if state.active_danger or (state.episode_id is None or state.episode_id!=frozen.episode_id):record['state']='superseded'
            tx.create(ref,record);return record
        return save(self.client.transaction())

    def record(self,action_id:str,*,sender_chat_id:int,message_chat_id:int,message_id:int,sender_hash:str,now:datetime)->tuple[ConfirmationStatus,str,str|None]:
        ref=self.client.collection(self.actions).document(action_id)
        confirmation_ref=self.client.collection(self.confirmations).document(action_id)
        @firestore.transactional
        def confirm(tx):
            action=ref.get(transaction=tx).to_dict() or {}
            if not action or sender_chat_id!=message_chat_id or sender_hash not in action.get('recipient_hashes',[]):return 'unavailable','en',None
            shop=self.client.collection(self.shops).document(action['shop_id']).get(transaction=tx).to_dict() or {}
            risk=self.client.collection(self.risks).document(action['shop_id']).get(transaction=tx).to_dict() or {}
            alert_id=sha256(f"{action['event_id']}:{action['shop_id']}:{sender_hash}".encode()).hexdigest()
            alert=self.client.collection(self.alerts).document(alert_id).get(transaction=tx).to_dict() or {}
            existing=confirmation_ref.get(transaction=tx)
            member=next((r for r in shop.get('recipients',[]) if r.get('telegram_chat_id')==sender_chat_id and r.get('role') in ('owner','worker')),None)
            if not member or alert.get('message_id')!=message_id or alert.get('status')!='accepted':return 'unavailable','en',None
            language=member['language'];state=ActiveRiskStore._view(risk,shop)
            if action['state']!='active' or action.get('danger_generation',0)!=risk.get('danger_generation',0) or state.active_danger or (state.episode_id is None or state.episode_id!=action['episode_id']):return 'superseded',language,None
            snapshot=ActionSnapshot.model_validate(action['snapshot']);displayed=ActionSnapshot.model_validate(alert['snapshot'])
            if action['kind']!='stock' or alert.get('level')!='warning' or snapshot!=displayed or displayed.stock_action_id!=action_id or not snapshot.items or not snapshot.inventory_id:return 'unavailable',language,None
            expected=round(sum(item.value_rm for item in snapshot.items),2)
            if abs(snapshot.estimated_value_rm-expected)>.005:return 'unavailable',language,None
            if existing.exists:return 'already_recorded',language,action_id
            tx.create(confirmation_ref,dict(confirmation_id=action_id,action_id=action_id,episode_id=action['episode_id'],
                event_id=action['event_id'],alert_id=alert_id,shop_id=action['shop_id'],kind='stock',protected_value_rm=expected,
                confirmed_at=now,is_demo=action['is_demo'],self_reported=True,confirmed_by_hash=sender_hash,
                snapshot=action['snapshot'],bigquery='pending'))
            return 'recorded',language,action_id
        return confirm(self.client.transaction(max_attempts=10))

class StockConfirmationService(VehicleConfirmationService):
    """Reuse the existing recipient hashing and bounded confirmation sink outbox."""

def estimated_lifted_value_sql(project:str,dataset:str)->str:
    """Synthetic dashboard metric: highest self-reported displayed snapshot per shop/episode."""
    if not all(value.replace('-','').replace('_','').isalnum() for value in (project,dataset)):
        raise ValueError('Invalid analytics identifier')
    return (f'SELECT COALESCE(SUM(value_rm),0) AS estimated_stock_value_reported_lifted FROM '
            f'(SELECT shop_id,episode_id,MAX(protected_value_rm) AS value_rm FROM `{project}.{dataset}.confirmations` '
            "WHERE is_demo=TRUE AND kind='stock' AND self_reported=TRUE GROUP BY shop_id,episode_id)")
