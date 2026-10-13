"""Localized basic replies and current Danger checks, independent of media intake."""
import asyncio
from typing import Any,Protocol
from api.alert_composer import render_danger
from api.destinations import DestinationLookup
from api.i18n import catalog,text
from api.inventory_models import InventoryReply

Shop = dict[str,Any]

class ReplyStore(Protocol):
    def shop_for_sender(self,sender_chat_id:int)->Shop|None: ...
    def danger_active(self,shop_id:str)->bool: ...

class ReplyGuard:
    def __init__(self,store:ReplyStore,*,destinations:DestinationLookup|None=None)->None:
        self.store,self.destinations=store,destinations

    async def danger_reply(self,shop:Shop)->InventoryReply:
        destination=await asyncio.to_thread(self.destinations.nearest,shop['lat'],shop['lng'],('pps','high_ground')) if self.destinations else None
        rendered,markup=render_danger(shop.get('language','en'),bool(shop.get('is_demo')),destination)
        return InventoryReply(text=rendered,reply_markup=markup,shop_id=shop['shop_id'],language=shop.get('language','en'),is_demo=bool(shop.get('is_demo')),kind='danger')

    async def reply(self,shop:Shop|None,key:str)->InventoryReply:
        shop=shop or {};language=shop.get('language','en')
        if shop.get('shop_id') and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        pieces=([text(language,'simulation_label')] if shop.get('is_demo') else [])+[text(language,key)]
        if not catalog(language)['_reviewed']:pieces.append(text(language,'translation_notice'))
        rendered='\n'.join(pieces)
        if len(rendered)>4096:raise ValueError('Localized reply exceeds Telegram limit')
        return InventoryReply(text=rendered,shop_id=shop.get('shop_id'),language=language,is_demo=bool(shop.get('is_demo')),kind='unavailable')

    async def recheck_reply(self,sender_chat_id:int,reply:InventoryReply)->InventoryReply:
        shop=await asyncio.to_thread(self.store.shop_for_sender,sender_chat_id)
        if shop and await asyncio.to_thread(self.store.danger_active,shop['shop_id']):return await self.danger_reply(shop)
        return reply
