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


class Message(BaseModel):
    message_id: StrictInt
    date: StrictInt | None = Field(default=None, ge=0)
    chat: Chat
    text: str | None = None
    location: Location | None = None
    video: 'VideoMedia | None' = None
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
    def __init__(self, inbox: FirestoreInbox, api: TelegramAPI, onboarding: "Onboarding | None" = None, confirmations=None, photos=None, inventory=None, stock_confirmations=None) -> None:
        self.inbox = inbox
        self.api = api
        self.onboarding = onboarding
        self.confirmations = confirmations
        self.photos = photos
        self.inventory = inventory
        self.stock_confirmations = stock_confirmations

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
        if message is None or message.chat.type != "private" or (not words and message.location is None and message.photo is None and message.video is None) or (self.onboarding is None and self.photos is None and self.inventory is None and (not words or words[0] != "/start")):
            await run_in_threadpool(self.inbox.transition, update.update_id, owner, "done", operation_id=operation_id, outcome="unsupported")
            return "done"
        media_reply = False
        reply_markup = None
        venue = None
        response_text = "Welcome to HighGround. Shop onboarding is not connected yet."
        if self.onboarding is not None or self.photos is not None or self.inventory is not None:
            location = {"lat": message.location.latitude, "lng": message.location.longitude} if message.location else None
            try:
                pending = await self.photos.pending_location_report_id(message.chat.id) if self.photos is not None and location else None
                if self.inventory is not None and message.video:
                    reply = await self.inventory.handle_video(message.chat.id, update.update_id, message.message_id, message.date, message.video, processing_started_at=received_at)
                elif self.inventory is not None and words and words[0] in ('/refresh','/inventory'):
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
        if self.inventory is not None:
            try:
                guarded = await self.inventory.recheck_reply(message.chat.id, InventoryReply(text=response_text, reply_markup=reply_markup, venue=venue, kind='prompt'))
                response_text, reply_markup, venue = guarded.text, guarded.reply_markup, guarded.venue
            except Exception:
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, 'retryable', operation_id=operation_id)
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
        await run_in_threadpool(self.inbox.transition, update.update_id, owner, "done", operation_id=operation_id, message_id=message_id)
        return "done"


    async def handle_callback(self, update: Update, owner: str, operation_id: str) -> Literal["done", "uncertain"]:
        from api.i18n import catalog, text
        query = update.callback_query
        status, language, confirmation_id = 'unavailable', 'en', None
        message = query.message
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
