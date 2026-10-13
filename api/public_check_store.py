"""Atomic sender-bound lookup intent, rate and sanitized replay cache only."""
from dataclasses import dataclass
from datetime import datetime,timedelta
from hashlib import sha256
from uuid import uuid4
from google.cloud import firestore
from api.agents.sessions import session_user_id
from api.public_check_models import CheckResult

@dataclass(frozen=True)
class IntentDecision:
    status:str
    intent_id:str|None=None
    owner:str|None=None
    result:CheckResult|None=None
    language:str='en'

class FirestoreCheckIntentStore:
    def __init__(self,client,hash_salt:str,*,intents='public_check_intents',senders='public_check_senders',operations='public_check_operations'):
        if not hash_salt:raise ValueError('Lookup hashing configuration required')
        self.client,self.hash_salt,self.intents,self.senders=client,hash_salt,intents,senders
        self.operations=operations
    def _identity(self,sender:int,operation:str):
        if type(sender) is not int or type(operation) is not str or not 1<=len(operation)<=128:raise ValueError('Invalid lookup operation')
        sender_hash=session_user_id(sender,self.hash_salt)
        return sender_hash,sha256((sender_hash+':'+operation).encode()).hexdigest()
    @staticmethod
    def _clock(now):
        if not isinstance(now,datetime) or now.tzinfo is None or now.utcoffset() is None:raise ValueError('Lookup clock must be aware')
    def open(self,sender:int,operation:str,now:datetime,*,language='en')->IntentDecision:
        from api.i18n import LANGUAGES
        if language not in LANGUAGES:raise ValueError('Unsupported lookup language')
        self._clock(now);sender_hash,identity=self._identity(sender,operation)
        ref=self.client.collection(self.intents).document(identity);gate=self.client.collection(self.senders).document(sender_hash)
        @firestore.transactional
        def begin(tx):
            old=ref.get(transaction=tx,timeout=5,retry=None).to_dict();state=gate.get(transaction=tx,timeout=5,retry=None).to_dict() or {}
            if old:return IntentDecision('expired' if now>=old['expires_at'] or state.get('active_intent')!=identity else old['status'],identity,language=old.get('language','en'))
            record={'sender_hash':sender_hash,'created_at':now,'expires_at':now+timedelta(minutes=5),'status':'waiting_location','language':language}
            tx.create(ref,record);tx.set(gate,{**state,'active_intent':identity})
            return IntentDecision('waiting_location',identity,language=language)
        return begin(self.client.transaction(max_attempts=5))
    def active(self,sender:int,now:datetime)->IntentDecision:
        self._clock(now);sender_hash,_=self._identity(sender,'active')
        state=self.client.collection(self.senders).document(sender_hash).get(timeout=5,retry=None).to_dict() or {}
        identity=state.get('active_intent')
        if identity is None:return IntentDecision('none')
        record=self.client.collection(self.intents).document(identity).get(timeout=5,retry=None).to_dict()
        if not record or record['sender_hash']!=sender_hash or now>=record['expires_at']:return IntentDecision('expired',identity)
        return IntentDecision(record['status'],identity,language=record.get('language','en'))

    def bound(self,sender:int,operation:str,now:datetime)->IntentDecision:
        """Original message binding contains no location or location fingerprint."""
        self._clock(now);sender_hash,key=self._identity(sender,operation)
        binding=self.client.collection(self.operations).document(key).get(timeout=5,retry=None).to_dict() or {}
        identity=binding.get('intent_id')
        if not identity:return IntentDecision('none')
        record=self.client.collection(self.intents).document(identity).get(timeout=5,retry=None).to_dict() or {}
        state=self.client.collection(self.senders).document(sender_hash).get(timeout=5,retry=None).to_dict() or {}
        if record.get('sender_hash')!=sender_hash or state.get('active_intent')!=identity or now>=record.get('expires_at',now):return IntentDecision('expired',identity)
        return IntentDecision(record['status'],identity,language=record.get('language','en'))
    def claim(self,sender:int,intent_id:str,operation:str,now:datetime)->IntentDecision:
        self._clock(now);sender_hash,operation_hash=self._identity(sender,operation)
        if len(intent_id)!=64 or any(c not in '0123456789abcdef' for c in intent_id):raise ValueError('Invalid lookup intent')
        ref=self.client.collection(self.intents).document(intent_id);gate=self.client.collection(self.senders).document(sender_hash);owner=uuid4().hex
        binding=self.client.collection(self.operations).document(operation_hash)
        @firestore.transactional
        def acquire(tx):
            record=ref.get(transaction=tx,timeout=5,retry=None).to_dict();state=gate.get(transaction=tx,timeout=5,retry=None).to_dict() or {}
            prior_binding=binding.get(transaction=tx,timeout=5,retry=None).to_dict()
            if prior_binding and prior_binding['intent_id']!=intent_id:return IntentDecision('consumed',intent_id)
            if not record or record['sender_hash']!=sender_hash:return IntentDecision('unauthorized')
            if now>=record['expires_at'] or state.get('active_intent')!=intent_id:return IntentDecision('expired',intent_id)
            previous=record.get('lookup_operation_hash')
            if previous is not None and previous!=operation_hash:return IntentDecision('consumed',intent_id)
            if record['status']=='complete':return IntentDecision('complete',intent_id,result=CheckResult.model_validate_json(record['result_json']))
            if record.get('lease_until',now)>now:return IntentDecision('busy',intent_id)
            if previous is None and state.get('next_lookup_at',now)>now:return IntentDecision('rate_limited',intent_id)
            tx.update(ref,{'status':'processing','lookup_operation_hash':operation_hash,'owner':owner,'lease_until':now+timedelta(seconds=60)})
            if not prior_binding:tx.create(binding,{'intent_id':intent_id})
            if previous is None:tx.update(gate,{'next_lookup_at':now+timedelta(seconds=30)})
            return IntentDecision('claimed',intent_id,owner)
        return acquire(self.client.transaction(max_attempts=5))
    def finish(self,sender:int,intent_id:str,owner:str,result:CheckResult,now:datetime)->IntentDecision:
        self._clock(now);sender_hash,_=self._identity(sender,'finish')
        ref=self.client.collection(self.intents).document(intent_id);gate=self.client.collection(self.senders).document(sender_hash)
        @firestore.transactional
        def complete(tx):
            record=ref.get(transaction=tx,timeout=5,retry=None).to_dict();state=gate.get(transaction=tx,timeout=5,retry=None).to_dict() or {}
            if not record or record['sender_hash']!=sender_hash or record.get('owner')!=owner:return IntentDecision('unauthorized')
            if now>=record['expires_at'] or state.get('active_intent')!=intent_id:return IntentDecision('expired',intent_id)
            if record['status']=='complete':return IntentDecision('complete',intent_id,result=CheckResult.model_validate_json(record['result_json']))
            tx.update(ref,{'status':'complete','result_json':result.model_dump_json(),'completed_at':now,'lease_until':now})
            return IntentDecision('complete',intent_id,result=result)
        return complete(self.client.transaction(max_attempts=5))
    def retryable(self,sender:int,intent_id:str,owner:str,now:datetime)->None:
        self._clock(now);sender_hash,_=self._identity(sender,'retry')
        ref=self.client.collection(self.intents).document(intent_id)
        @firestore.transactional
        def release(tx):
            record=ref.get(transaction=tx,timeout=5,retry=None).to_dict()
            if not record or record['sender_hash']!=sender_hash or record.get('owner')!=owner:raise ValueError('Lookup ownership mismatch')
            if record['status']=='processing':tx.update(ref,{'status':'retryable','lease_until':now})
        release(self.client.transaction(max_attempts=5))
