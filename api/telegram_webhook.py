"""Durable delivery of deterministic private onboarding replies."""
from typing import Literal, TYPE_CHECKING
import hashlib
import re
from datetime import UTC, datetime
from starlette.concurrency import run_in_threadpool

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictFloat

from api.telegram_inbox import FirestoreInbox
from api.tools.telegram import TelegramAPI, TelegramSendError
from api.inventory_models import VideoMedia, InventoryReply
from api.policy import PolicyDocument
from api.policy_models import PolicyReply


if TYPE_CHECKING:
    from api.onboarding import Onboarding


class Location(BaseModel):
    latitude: StrictFloat = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: StrictFloat = Field(ge=-180, le=180, allow_inf_nan=False)


class Chat(BaseModel):
    id: StrictInt
    type: str


class PhotoSize(BaseModel):
    file_id: str = Field(min_length=1, max_length=512)
    file_unique_id: str = Field(min_length=1, max_length=512)
    width: StrictInt = Field(gt=0)
    height: StrictInt = Field(gt=0)
    file_size: StrictInt | None = Field(default=None, gt=0)


class Document(BaseModel):
    file_id:str=Field(min_length=1,max_length=512)
    file_unique_id:str=Field(min_length=1,max_length=256)
    file_size:StrictInt|None=Field(default=None,gt=0)
    mime_type:str|None=Field(default=None,max_length=100)


class Message(BaseModel):
    message_id: StrictInt
    date: StrictInt | None = Field(default=None, ge=0)
    chat: Chat
    text: str | None = None
    location: Location | None = None
    video: 'VideoMedia | None' = None
    document:Document|None=None
    photo: list[PhotoSize] | None = Field(default=None, min_length=1, max_length=20)


class CallbackSender(BaseModel):
    id: StrictInt = Field(ge=1)


class CallbackQuery(BaseModel):
    id: str = Field(min_length=1, max_length=256)
    sender: CallbackSender = Field(alias='from')
    message: Message | None = None
    data: str | None = Field(default=None, max_length=64)


class Update(BaseModel):
    model_config = ConfigDict(extra="ignore")
    update_id: StrictInt = Field(ge=0)
    message: Message | None = None
    callback_query: CallbackQuery | None = None


class WebhookRetry(Exception):
    """Durable state is unavailable or processing should be retried."""


class TelegramHandler:
    def __init__(self, inbox: FirestoreInbox, api: TelegramAPI, onboarding: "Onboarding | None" = None, confirmations=None, photos=None, inventory=None, stock_confirmations=None, recovery=None, cards=None, policy=None, waste=None, public_check=None, outcomes=None) -> None:
        self.inbox = inbox
        self.api = api
        self.onboarding = onboarding
        self.confirmations = confirmations
        self.photos = photos
        self.inventory = inventory
        self.stock_confirmations = stock_confirmations
        self.recovery = recovery
        self.cards = cards
        self.policy = policy
        self.waste = waste
        self.public_check = public_check
        self.outcomes=outcomes

    async def check_location_flow_waiting(self,sender):
        pending=await self.photos.pending_location_report_id(sender) if self.photos else None
        onboarding=await self.onboarding.waiting_location(sender) if self.onboarding and hasattr(self.onboarding,'waiting_location') else False
        return bool(pending or onboarding)

    async def handle(self, update: Update) -> Literal["done", "uncertain"]:
        received_at = datetime.now(UTC)
        message = update.message
        operation_id = hashlib.sha256(f"{update.update_id}:{message.date}".encode()).hexdigest() if message and message.date is not None else None
        if update.callback_query is not None:
            operation_id = hashlib.sha256(('callback:' + update.callback_query.id).encode()).hexdigest()
        status, owner = await run_in_threadpool(self.inbox.claim, update.update_id, operation_id)
        if status == "busy":
            raise WebhookRetry()
        if status in ("done", "uncertain"):
            return status
        if update.callback_query is not None:
            return await self.handle_callback(update, owner, operation_id)
        message = update.message
        words = message.text.split() if message and message.text else []
        if message is None or message.chat.type != "private" or (not words and message.location is None and message.photo is None and message.video is None and message.document is None) or (self.onboarding is None and self.photos is None and self.inventory is None and self.recovery is None and self.cards is None and self.policy is None and self.waste is None and self.public_check is None and self.outcomes is None and (not words or words[0] != "/start")):
            await run_in_threadpool(self.inbox.transition, update.update_id, owner, "done", operation_id=operation_id, outcome="unsupported")
            return "done"
        media_reply = False
        policy_reply = False
        waste_reply = False
        check_reply = False
        outcome_reply=False
        reply_markup = None
        venue = None
        response_text = "Welcome to HighGround. Shop onboarding is not connected yet."
        if self.onboarding is not None or self.photos is not None or self.inventory is not None or self.recovery is not None or self.cards is not None or self.policy is not None or self.waste is not None or self.public_check is not None or self.outcomes is not None:
            location = {"lat": message.location.latitude, "lng": message.location.longitude} if message.location else None
            try:
                pending = await self.photos.pending_location_report_id(message.chat.id) if self.photos is not None and location else None
                recovery_context = await self.recovery.active_context(message.chat.id,message.message_id,message.video.file_unique_id if message.video else max(message.photo,key=lambda item:(item.width*item.height,item.file_size or 0)).file_unique_id if message.photo else None) if self.recovery and (message.video or message.photo or (words and words[0]=='/report')) else None
                largest=max(message.photo,key=lambda item:(item.width*item.height,item.file_size or 0)) if message.photo else None
                flood_bound=await self.photos.bound_photo_report(message.chat.id,message.message_id,largest.file_unique_id) if largest and self.photos and hasattr(self.photos,'bound_photo_report') else None
                policy_context=await self.policy.active_context(message.chat.id,message.message_id,message.document.file_unique_id if message.document else largest.file_unique_id if largest else None) if self.policy and (message.photo or message.document or (words and words[0] in ('/policy','/cancel'))) else None
                check_operation=f'message:{message.message_id}:{message.date}'
                check_context,check_bound=await self.public_check.context(message.chat.id,check_operation) if self.public_check and location else (None,False)
                check_waiting=await self.check_location_flow_waiting(message.chat.id) if self.public_check and (location or (words and words[0]=='/check')) else False
                if self.outcomes and words and words[0]=='/outcome':
                    outcome_reply=True
                    valid=len(words) in (3,4) and words[1]=='inside'
                    depth=int(words[3]) if valid and len(words)==4 and re.fullmatch(r'[0-9]{1,4}',words[3]) else None
                    if len(words)==4 and depth is None:valid=False
                    reply=await self.outcomes.owner_report(message.chat.id,words[2] if valid else '',depth)
                elif self.public_check and words and words[0]=='/check':
                    check_reply=True
                    reply=await self.public_check.start(message.chat.id,check_operation,registered_flow_waiting=check_waiting,language_hint=words[1] if len(words)==2 else None)
                elif self.public_check and location and check_context and (check_bound or not check_waiting):
                    from api.public_check_models import CheckLocation
                    check_reply=True;reply=await self.public_check.lookup(message.chat.id,check_operation,CheckLocation(**location),check_context)
                elif self.waste and words and words[0]=='/street':
                    waste_reply=True;reply=await self.waste.street(message.chat.id,message.text.partition(' ')[2].strip(),operation_id)
                elif self.waste and len(words)==2 and words[0]=='/start' and re.fullmatch(r'donate_[0-9a-f]{32}',words[1]):
                    waste_reply=True;reply=await self.waste.donation(message.chat.id,words[1][7:])
                elif self.policy and words and words[0]=='/policy':
                    policy_reply=True
                    if len(words)==2 and words[1]=='done':reply=await self.policy.done(message.chat.id)
                    elif len(words)==2 and words[1]=='cancel':reply=await self.policy.cancel(message.chat.id)
                    elif len(words)==2 and words[1]=='keep' and policy_context:reply=await self.policy.choose_keep(message.chat.id,policy_context['intake_id'])
                    else:reply=await self.policy.start(message.chat.id,operation_id)
                elif self.policy and policy_context and words and words[0]=='/cancel':
                    policy_reply=True;reply=await self.policy.cancel(message.chat.id)
                elif self.policy and message.document:
                    policy_reply=True
                    reply=await self.policy.handle_document(message.chat.id,update.update_id,message.message_id,message.date,PolicyDocument(file_id=message.document.file_id,file_unique_id=message.document.file_unique_id,file_size=message.document.file_size,mime_type=message.document.mime_type or 'application/octet-stream'),processing_started_at=received_at)
                elif self.policy and policy_context and largest and not flood_bound and (policy_context.get('bound_upload') or not recovery_context or not recovery_context.get('bound_upload')):
                    policy_reply=True
                    reply=await self.policy.handle_photo(message.chat.id,update.update_id,message.message_id,message.date,PolicyDocument(file_id=largest.file_id,file_unique_id=largest.file_unique_id,file_size=largest.file_size,mime_type='image/jpeg'),processing_started_at=received_at)
                elif self.cards is not None and words and words[0]=='/card':
                    card_status, reply = await self.cards.request_owner(message.chat.id,operation_id)
                    if card_status in ('accepted','uncertain','busy'):
                        await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,outcome='card_'+card_status)
                        return 'done'
                elif self.recovery and words and words[0]=='/cancel':
                    reply = await self.recovery.exit(message.chat.id)
                elif self.recovery and words and words[0]=='/waterline':
                    reply = await self.recovery.request_photo(message.chat.id)
                elif self.recovery and words and words[0]=='/report':
                    reply = await self.recovery.declare(message.chat.id,recovery_context['report_id']) if len(words)==2 and words[1]=='confirm' and recovery_context else await self.recovery.start(message.chat.id,str(update.update_id))
                elif self.recovery and recovery_context and message.video:
                    reply = await self.recovery.handle_video(message.chat.id, update.update_id, message.message_id, message.date, message.video, processing_started_at=received_at)
                elif self.recovery and recovery_context and message.photo:
                    from api.photo_models import PhotoMedia
                    largest = max(message.photo,key=lambda item:(item.width*item.height,item.file_size or 0))
                    reply = await self.recovery.handle_photo(message.chat.id,update.update_id,message.message_id,message.date,PhotoMedia(file_id=largest.file_id,file_unique_id=largest.file_unique_id,file_size=largest.file_size),processing_started_at=received_at)
                elif self.inventory is not None and message.video:
                    reply = await self.inventory.handle_video(message.chat.id, update.update_id, message.message_id, message.date, message.video, processing_started_at=received_at)
                elif self.inventory is not None and words and words[0] in ('/refresh','/inventory'):
                    if self.recovery:await self.recovery.exit(message.chat.id)
                    reply = await self.inventory.request_video(message.chat.id)
                elif self.photos is not None and message.photo:
                    media_reply = True
                    from api.photo_models import PhotoMedia
                    largest = max(message.photo, key=lambda item: (item.width * item.height, item.file_size or 0))
                    reply = await self.photos.handle_photo(message.chat.id, update.update_id, message.message_id, message.date,
                                                          PhotoMedia(file_id=largest.file_id, file_unique_id=largest.file_unique_id, file_size=largest.file_size),
                                                          processing_started_at=received_at)
                elif pending:
                    media_reply = True
                    reply = await self.photos.confirm_report_location(message.chat.id, pending, lat=location['lat'], lng=location['lng'])
                else:
                    if self.onboarding is None:
                        await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,outcome='unsupported')
                        return 'done'
                    reply = await self.onboarding.process(message.chat.id, update.update_id, message.text, location, message.date)
            except Exception:
                # No external send has begun; committed session/domain writes
                # recover idempotently on the next delivery.
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, "retryable", operation_id=operation_id)
                raise WebhookRetry() from None
            response_text, reply_markup, venue = reply.text, reply.reply_markup, reply.venue
        await run_in_threadpool(self.inbox.transition, update.update_id, owner, "sending", operation_id=operation_id)
        if media_reply:
            try:
                reply = await self.photos.recheck_reply(message.chat.id, reply)
                response_text, reply_markup, venue = reply.text, reply.reply_markup, reply.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'retryable', operation_id=operation_id)
                raise WebhookRetry() from None
        if self.recovery is not None:
            try:
                guarded = await self.recovery.recheck_reply(message.chat.id, InventoryReply(text=response_text, reply_markup=reply_markup, venue=venue, kind='prompt'))
                response_text, reply_markup, venue = guarded.text, guarded.reply_markup, guarded.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
        if self.inventory is not None:
            try:
                guarded = await self.inventory.recheck_reply(message.chat.id, InventoryReply(text=response_text, reply_markup=reply_markup, venue=venue, kind='prompt'))
                response_text, reply_markup, venue = guarded.text, guarded.reply_markup, guarded.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'retryable', operation_id=operation_id)
                raise WebhookRetry() from None
        if policy_reply:
            try:
                reply=await self.policy.recheck_reply(message.chat.id,reply)
                response_text,reply_markup,venue=reply.text,reply.reply_markup,reply.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
        if waste_reply:
            try:
                reply=await self.waste.recheck_reply(message.chat.id,reply)
                response_text,reply_markup,venue=reply.text,reply.reply_markup,reply.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
        if outcome_reply:
            try:
                reply=await self.outcomes.recheck_reply(message.chat.id,reply)
                response_text,reply_markup,venue=reply.text,reply.reply_markup,reply.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
        if check_reply:
            try:
                waiting=await self.check_location_flow_waiting(message.chat.id) if getattr(reply,'location_request',False) else False
                reply=await self.public_check.recheck_reply(message.chat.id,reply,registered_flow_waiting=waiting)
                response_text,reply_markup,venue=reply.text,reply.reply_markup,reply.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
        try:
            if venue is not None:
                message_id = await run_in_threadpool(self.api.send_venue, message.chat.id, **venue, reply_markup=reply_markup)
            else:
                message_id = await run_in_threadpool(self.api.send_message, message.chat.id, response_text, reply_markup=reply_markup)
        except TelegramSendError as error:
            state = "uncertain" if error.uncertain else "retryable"
            await run_in_threadpool(self.inbox.transition, update.update_id, owner, state, operation_id=operation_id)
            if error.uncertain:
                return "uncertain"
            raise WebhookRetry() from None
        if policy_reply and reply.disclosure and reply.kind!='danger':
            try:await self.policy.mark_disclosed(message.chat.id,reply.intake_id,message_id)
            except Exception:
                # Send was accepted; keep intake closed rather than claiming notice delivery.
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain',operation_id=operation_id)
                return 'uncertain'
        await run_in_threadpool(self.inbox.transition, update.update_id, owner, "done", operation_id=operation_id, message_id=message_id)
        return "done"


    async def handle_callback(self, update: Update, owner: str, operation_id: str) -> Literal["done", "uncertain"]:
        from api.i18n import catalog, text
        query = update.callback_query
        status, language, confirmation_id = 'unavailable', 'en', None
        message = query.message
        if self.inventory and query.data=='inventory:refresh' and message and message.chat.type=='private' and query.sender.id==message.chat.id:
            try:await run_in_threadpool(self.api.answer_callback_query,query.id,'')
            except TelegramSendError:pass
            try:
                reply=await self.inventory.warning_update(query.sender.id)
                if reply.kind=='prompt' and self.recovery:await self.recovery.exit(query.sender.id)
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'sending',operation_id=operation_id)
                reply=await self.inventory.warning_update(query.sender.id,reply)
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            try:sent_id=await run_in_threadpool(self.api.send_message,query.sender.id,reply.text,reply_markup=reply.reply_markup)
            except TelegramSendError as error:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain' if error.uncertain else 'retryable',operation_id=operation_id)
                if error.uncertain:return 'uncertain'
                raise WebhookRetry() from None
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain',operation_id=operation_id)
                return 'uncertain'
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,message_id=sent_id)
            return 'done'
        outcome_match=re.fullmatch(r'outcome:([0-9a-f]{32}):(no|street|entrance|inside)',query.data or '')
        if self.outcomes and outcome_match and message and message.chat.type=='private' and query.sender.id==message.chat.id:
            try:await run_in_threadpool(self.api.answer_callback_query,query.id,'')
            except TelegramSendError:pass
            try:reply=await self.outcomes.answer(query.sender.id,outcome_match[1],message.message_id,'street_only' if outcome_match[2]=='street' else outcome_match[2])
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'sending',operation_id=operation_id)
            try:reply=await self.outcomes.recheck_reply(query.sender.id,reply)
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            try:sent_id=await run_in_threadpool(self.api.send_message,query.sender.id,reply.text,reply_markup=reply.reply_markup)
            except TelegramSendError as error:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain' if error.uncertain else 'retryable',operation_id=operation_id)
                if error.uncertain:return 'uncertain'
                raise WebhookRetry() from None
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain',operation_id=operation_id)
                return 'uncertain'
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,message_id=sent_id)
            return 'done'
        waste_match=re.fullmatch(r'waste:(street|donate|revoke):([0-9a-f]{32})',query.data or '')
        if self.waste and waste_match and message and message.chat.type=='private' and query.sender.id==message.chat.id:
            try:await run_in_threadpool(self.api.answer_callback_query,query.id,'')
            except TelegramSendError:pass
            try:reply=await self.waste.confirm(query.sender.id,waste_match[1],waste_match[2],operation_id)
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'sending',operation_id=operation_id)
            try:reply=await self.waste.recheck_reply(query.sender.id,reply)
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            try:sent_id=await run_in_threadpool(self.api.send_message,query.sender.id,reply.text,reply_markup=reply.reply_markup)
            except TelegramSendError as error:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain' if error.uncertain else 'retryable',operation_id=operation_id)
                if error.uncertain:return 'uncertain'
                raise WebhookRetry() from None
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain',operation_id=operation_id)
                return 'uncertain'
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,message_id=sent_id)
            return 'done'
        policy_match=re.fullmatch(r'policy:(keep|done|cancel|delete|copy):([0-9a-f]{32})(?::([0-4]))?',query.data or '')
        if self.policy and policy_match and message and message.chat.type=='private' and query.sender.id==message.chat.id:
            try:await run_in_threadpool(self.api.answer_callback_query,query.id,'')
            except TelegramSendError:pass
            action,intake_id,index=policy_match.groups();document=None
            try:
                if action=='copy' and index is not None:
                    result=await self.policy.copy_for_sender(query.sender.id,intake_id,int(index))
                    if isinstance(result,PolicyReply):reply=result
                    else:
                        document=result
                        reply=PolicyReply(text='',kind='policy_result')
                elif action=='keep' and index is None:reply=await self.policy.choose_keep(query.sender.id,intake_id)
                elif action=='done' and index is None:reply=await self.policy.done(query.sender.id,intake_id)
                elif action=='cancel' and index is None:reply=await self.policy.cancel(query.sender.id,intake_id)
                elif action=='delete' and index is None:reply=await self.policy.delete_copy(query.sender.id,intake_id)
                else:raise PermissionError('Invalid policy control')
                reply=await self.policy.recheck_reply(query.sender.id,reply)
                if reply.kind=='danger':document=None
            except PermissionError:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,outcome='policy_unauthorized')
                return 'done'
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'sending',operation_id=operation_id)
            try:
                reply=await self.policy.recheck_copy(query.sender.id,intake_id,int(index),document) if document else await self.policy.recheck_reply(query.sender.id,reply)
                if reply.kind=='danger':document=None
            except PermissionError:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,outcome='policy_unauthorized')
                return 'done'
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            try:
                if document:
                    mime=document.record.mime_type;extension={'application/pdf':'pdf','image/jpeg':'jpg','image/png':'png','image/webp':'webp'}[mime]
                    sent_id=await run_in_threadpool(self.api.send_document,query.sender.id,document.original_bytes,mime,f'policy-page-{int(index)+1}.{extension}')
                else:sent_id=await run_in_threadpool(self.api.send_message,query.sender.id,reply.text,reply_markup=reply.reply_markup)
            except TelegramSendError as error:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain' if error.uncertain else 'retryable',operation_id=operation_id)
                if error.uncertain:return 'uncertain'
                raise WebhookRetry() from None
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain',operation_id=operation_id)
                return 'uncertain'
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,message_id=sent_id)
            return 'done'
        recovery_match = re.fullmatch(r'recovery:([0-9a-f]{32})', query.data or '')
        if self.recovery and recovery_match and message and message.chat.type=='private' and query.sender.id==message.chat.id:
            try:
                await run_in_threadpool(self.api.answer_callback_query,query.id,'')
            except TelegramSendError:
                pass
            try:
                reply=await self.recovery.declare(query.sender.id,recovery_match[1])
                reply=await self.recovery.recheck_reply(query.sender.id,reply)
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'retryable',operation_id=operation_id)
                raise WebhookRetry() from None
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'sending',operation_id=operation_id)
            try:
                sent_id=await run_in_threadpool(self.api.send_message,query.sender.id,reply.text,reply_markup=reply.reply_markup)
            except TelegramSendError as error:
                state='uncertain' if error.uncertain else 'retryable'
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,state,operation_id=operation_id)
                if error.uncertain:return 'uncertain'
                raise WebhookRetry() from None
            except Exception:
                await run_in_threadpool(self.inbox.transition,update.update_id,owner,'uncertain',operation_id=operation_id)
                return 'uncertain'
            await run_in_threadpool(self.inbox.transition,update.update_id,owner,'done',operation_id=operation_id,message_id=sent_id)
            return 'done'
        photo_match = re.fullmatch(r'photo:([0-9a-f]{32}):(yes|no)', query.data or '')
        if self.photos is not None and photo_match and message is not None and message.chat.type == 'private' and query.sender.id == message.chat.id:
            try:
                await run_in_threadpool(self.api.answer_callback_query, query.id, '')
            except TelegramSendError:
                pass
            try:
                reply = await self.photos.confirm_report_location(query.sender.id, photo_match[1], at_shop=photo_match[2] == 'yes')
            except Exception:
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'retryable', operation_id=operation_id)
                raise WebhookRetry() from None
            await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'sending', operation_id=operation_id)
            try:
                reply = await self.photos.recheck_reply(query.sender.id, reply)
            except Exception:
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'retryable', operation_id=operation_id)
                raise WebhookRetry() from None
            try:
                if reply.venue is not None:
                    sent_id = await run_in_threadpool(self.api.send_venue, query.sender.id, **reply.venue, reply_markup=reply.reply_markup)
                else:
                    sent_id = await run_in_threadpool(self.api.send_message, query.sender.id, reply.text, reply_markup=reply.reply_markup)
            except TelegramSendError as error:
                state = 'uncertain' if error.uncertain else 'retryable'
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, state, operation_id=operation_id)
                if error.uncertain:
                    return 'uncertain'
                raise WebhookRetry() from None
            await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'done', operation_id=operation_id, message_id=sent_id)
            return 'done'
        if self.confirmations is not None and message is not None and message.chat.type == 'private' and re.fullmatch(r'vehicle:[0-9a-f]{32}', query.data or ''):
            status, language, confirmation_id = await self.confirmations.record(query.data.split(':')[1], sender_chat_id=query.sender.id,
                                                                             message_chat_id=message.chat.id, message_id=message.message_id)
        stock_callback = bool(re.fullmatch(r'stock:[0-9a-f]{32}', query.data or ''))
        if self.stock_confirmations is not None and stock_callback and message is not None and message.chat.type == 'private':
            status, language, confirmation_id = await self.stock_confirmations.record(query.data.split(':')[1], sender_chat_id=query.sender.id, message_chat_id=message.chat.id, message_id=message.message_id)
        key = {'recorded': 'stock_recorded' if stock_callback else 'vehicle_recorded', 'already_recorded': 'stock_already_recorded' if stock_callback else 'vehicle_already_recorded',
               'superseded': 'confirmation_superseded', 'unavailable': 'confirmation_unavailable'}[status]
        feedback = text(language, key)
        if not catalog(language)['_reviewed']:
            feedback += '\n' + text(language, 'translation_notice')
        # Acknowledge before the optional analytics sink; the domain result is durable.
        try:
            await run_in_threadpool(self.api.answer_callback_query, query.id, feedback)
        except TelegramSendError:
            pass  # Expired/ambiguous callback answer does not undo completion.
        if confirmation_id:
            await (self.stock_confirmations if stock_callback else self.confirmations).flush(confirmation_id)
        await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'done', operation_id=operation_id, outcome=status)
        return 'done'
