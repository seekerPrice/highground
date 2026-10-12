"""Durable delivery of deterministic private onboarding replies."""
from typing import Literal, TYPE_CHECKING
import hashlib
from starlette.concurrency import run_in_threadpool

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictFloat

from api.telegram_inbox import FirestoreInbox
from api.tools.telegram import TelegramAPI, TelegramSendError


if TYPE_CHECKING:
    from api.onboarding import Onboarding


class Location(BaseModel):
    latitude: StrictFloat = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: StrictFloat = Field(ge=-180, le=180, allow_inf_nan=False)


class Chat(BaseModel):
    id: StrictInt
    type: str


class Message(BaseModel):
    message_id: StrictInt
    date: StrictInt | None = Field(default=None, ge=0)
    chat: Chat
    text: str | None = None
    location: Location | None = None


class Update(BaseModel):
    model_config = ConfigDict(extra="ignore")
    update_id: StrictInt = Field(ge=0)
    message: Message | None = None


class WebhookRetry(Exception):
    """Durable state is unavailable or processing should be retried."""


class TelegramHandler:
    def __init__(self, inbox: FirestoreInbox, api: TelegramAPI, onboarding: "Onboarding | None" = None) -> None:
        self.inbox = inbox
        self.api = api
        self.onboarding = onboarding

    async def handle(self, update: Update) -> Literal["done", "uncertain"]:
        message = update.message
        operation_id = hashlib.sha256(f"{update.update_id}:{message.date}".encode()).hexdigest() if message and message.date is not None else None
        status, owner = await run_in_threadpool(self.inbox.claim, update.update_id, operation_id)
        if status == "busy":
            raise WebhookRetry()
        if status in ("done", "uncertain"):
            return status
        message = update.message
        words = message.text.split() if message and message.text else []
        if message is None or message.chat.type != "private" or (not words and message.location is None) or (self.onboarding is None and (not words or words[0] != "/start")):
            await run_in_threadpool(self.inbox.transition, update.update_id, owner, "done", operation_id=operation_id, outcome="unsupported")
            return "done"
        reply_markup = None
        venue = None
        response_text = "Welcome to HighGround. Shop onboarding is not connected yet."
        if self.onboarding is not None:
            location = {"lat": message.location.latitude, "lng": message.location.longitude} if message.location else None
            try:
                reply = await self.onboarding.process(message.chat.id, update.update_id, message.text, location, message.date)
            except Exception:
                # No external send has begun; committed session/domain writes
                # recover idempotently on the next delivery.
                await run_in_threadpool(self.inbox.transition, update.update_id, owner, "retryable", operation_id=operation_id)
                raise WebhookRetry() from None
            response_text, reply_markup, venue = reply.text, reply.reply_markup, reply.venue
        await run_in_threadpool(self.inbox.transition, update.update_id, owner, "sending", operation_id=operation_id)
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
