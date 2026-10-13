"""Exercise real factory lifecycle/authorization seams with owned fake clients."""
import asyncio
from types import SimpleNamespace
from api.config import Settings
from api.policy import create_policy_service
from api.agents.sessions import session_user_id

class Client:
    def __init__(self):self.closed=False
    def close(self):self.closed=True
class Store:
    hash_salt='synthetic'
    def owner_shop(self,sender):return {'shop_id':'shop'} if sender==123 else None
    def get(self,intake):return {'shop_id':'shop','sender_hash':session_user_id(123,self.hash_salt)}
    def original_binding(self,media):return None

def test_real_factory_owner_authorization_is_callable_and_clients_close(monkeypatch):
    client=Client();storage=Client();store=Store();store.client=client
    monkeypatch.setattr('api.tools.firestore.create_firestore_client',lambda settings:client)
    monkeypatch.setattr('api.active_risk.ActiveRiskStore',lambda *args,**kwargs:None)
    monkeypatch.setattr('api.destinations.DestinationLookup',lambda *args,**kwargs:None)
    monkeypatch.setattr('api.policy_store.PolicyStore',lambda *args,**kwargs:store)
    monkeypatch.setattr('api.tools.storage.create_storage_client',lambda settings:storage)
    monkeypatch.setattr('api.policy_media.PolicyStorage',lambda *args,**kwargs:storage)
    monkeypatch.setattr('api.policy_media.PolicyMediaStore',lambda *args,**kwargs:None)
    monkeypatch.setattr('api.media.MediaService',lambda *args,**kwargs:SimpleNamespace(authorize=None))
    class Assessor:
        async def close(self):pass
    monkeypatch.setattr('api.agents.policy.PolicyAssessor',lambda settings:Assessor())
    active=create_policy_service(Settings(gcp_project='synthetic',hash_salt='synthetic',gcs_bucket='private',telegram_bot_token='synthetic'))
    async def run():
        try:assert (await active._owned(123,'a'*32))['shop_id']=='shop'
        finally:await active.close()
    asyncio.run(run())
    assert client.closed and storage.closed
