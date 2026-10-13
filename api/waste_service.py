"""Owner confirmations only; report capabilities never authorize these writes."""
import asyncio
import re
from api.reply_guard import ReplyGuard,Shop
from api.destinations import DestinationLookup
from api.config import Settings
from api.i18n import text
from api.waste_store import WasteStore
from api.inventory_models import InventoryReply

class WasteReply(InventoryReply):
    action_id:str|None=None
    owner_required:bool=False

class WasteService:
    def __init__(self,store:WasteStore,*,destinations:DestinationLookup|None=None,owns_clients:bool=False)->None:
        self.store=store;self.guard=ReplyGuard(store,destinations=destinations)
        self.owns_clients=owns_clients

    async def danger_reply(self,shop:Shop)->InventoryReply:
        return await self.guard.danger_reply(shop)

    async def reply(self,shop:Shop|None,key:str)->InventoryReply:
        return await self.guard.reply(shop,key)

    async def _failure(self,sender:int)->InventoryReply:
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender)
        return await self.reply(shop,'waste_action_unavailable')

    async def street(self,sender:int,label:str|None,operation:str)->InventoryReply:
        shop=await asyncio.to_thread(self.store.owner_shop,sender)
        if not shop:return await self._failure(sender)
        if not label:
            reply=await self.reply(shop,'waste_street_instructions')
            return WasteReply(**reply.model_dump(),owner_required=True)
        try:action=await asyncio.to_thread(self.store.stage_street,sender,label,operation)
        except (PermissionError,ValueError):return await self._failure(sender)
        reply=await self.reply(shop,'waste_street_confirm')
        if reply.kind=='danger':return reply
        return WasteReply(**(reply.model_dump()|{'text':reply.text+'\n'+action['label'],'action_id':action['action_id'],'owner_required':True,
            'reply_markup':{'inline_keyboard':[[{'text':text(shop['language'],'waste_confirm_button'),'callback_data':'waste:street:'+action['action_id']}]]}}))

    async def donation(self,sender:int,identity:str)->InventoryReply:
        if not re.fullmatch('[0-9a-f]{32}',identity):return await self._failure(sender)
        try:action=await asyncio.to_thread(self.store.action,identity,sender)
        except (PermissionError,ValueError):return await self._failure(sender)
        if action['kind']!='donation':return await self._failure(sender)
        shop=await asyncio.to_thread(self.store.owner_shop,sender)
        reply=await self.reply(shop,'waste_donation_confirm')
        if reply.kind=='danger':return reply
        available=action.get('available') is True
        return WasteReply(**(reply.model_dump()|{'text':reply.text+'\n'+action.get('item_name','Item'),'action_id':identity,'owner_required':True,
            'reply_markup':{'inline_keyboard':[[{'text':text(shop['language'],'waste_revoke_button' if available else 'waste_confirm_button'),'callback_data':('waste:revoke:' if available else 'waste:donate:')+identity}]]}}))

    async def confirm(self,sender:int,kind:str,identity:str,operation:str)->InventoryReply:
        try:
            action=await asyncio.to_thread(self.store.action,identity,sender)
            if action['kind']!=('street' if kind=='street' else 'donation') or kind not in ('street','donate','revoke'):raise PermissionError()
            await asyncio.to_thread(self.store.confirm,identity,sender,available=kind!='revoke',operation=operation)
        except (PermissionError,ValueError):return await self._failure(sender)
        shop=await asyncio.to_thread(self.store.owner_shop,sender)
        return await self.reply(shop,'waste_street_recorded' if kind=='street' else 'waste_donation_recorded')

    async def close(self)->None:
        if self.owns_clients:self.store.client.close()

    async def recheck_reply(self,sender:int,reply:InventoryReply)->InventoryReply:
        guarded=await self.guard.recheck_reply(sender,reply)
        if guarded.kind=='danger':return guarded
        if getattr(reply,'owner_required',False) and not await asyncio.to_thread(self.store.owner_shop,sender):return await self._failure(sender)
        if getattr(reply,'action_id',None):
            try:await asyncio.to_thread(self.store.action,reply.action_id,sender)
            except (PermissionError,ValueError):return await self._failure(sender)
        return guarded


def create_waste_service(settings:Settings)->WasteService:
    from api.tools.firestore import create_firestore_client
    from api.active_risk import ActiveRiskStore
    from api.destinations import DestinationLookup
    client=create_firestore_client(settings)
    return WasteService(WasteStore(client,settings.hash_salt,risks=ActiveRiskStore(client,max_age=settings.official_max_age)),destinations=DestinationLookup(client,radius_m=settings.destination_search_radius_m),owns_clients=True)

class LazyWasteService:
    def __init__(self,settings:Settings)->None:self.settings=settings;self.active=None
    def _service(self)->WasteService:
        if self.active is None:self.active=create_waste_service(self.settings)
        return self.active
    async def street(self,sender:int,label:str|None,operation:str)->InventoryReply:return await self._service().street(sender,label,operation)
    async def donation(self,sender:int,identity:str)->InventoryReply:return await self._service().donation(sender,identity)
    async def confirm(self,sender:int,kind:str,identity:str,operation:str)->InventoryReply:return await self._service().confirm(sender,kind,identity,operation)
    async def recheck_reply(self,sender:int,reply:InventoryReply)->InventoryReply:
        # Handler calls this only on waste replies; ordinary replies construct nothing.
        return await self._service().recheck_reply(sender,reply)
    async def close(self)->None:
        if self.active:await self.active.close()
