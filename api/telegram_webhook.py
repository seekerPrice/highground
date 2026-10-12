"""Minimal private /start processing; onboarding belongs to Task 5."""
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from api.telegram_inbox import FirestoreInbox
from api.tools.telegram import TelegramAPI, TelegramSendError


class Chat(BaseModel):
    id: StrictInt
    type: str


class Message(BaseModel):
    message_id: StrictInt
    chat: Chat
    text: str | None = None


class Update(BaseModel):
    model_config = ConfigDict(extra="ignore")
    update_id: StrictInt = Field(ge=0)
    message: Message | None = None


class WebhookRetry(Exception):
    """Durable state is unavailable or processing should be retried."""


class TelegramHandler:
    def __init__(self, inbox: FirestoreInbox, api: TelegramAPI) -> None:
        self.inbox = inbox
        self.api = api

    def handle(self, update: Update, payload: dict[str, Any]) -> Literal["done", "uncertain"]:
        status, owner = self.inbox.claim(update.update_id, payload)
        if status == "busy":
            raise WebhookRetry()
        if status in ("done", "uncertain"):
            return status
        message = update.message
        words = message.text.split() if message and message.text else []
        if message is None or message.chat.type != "private" or not words or words[0] != "/start":
            self.inbox.transition(update.update_id, owner, "done", outcome="unsupported")
            return "done"
        self.inbox.transition(update.update_id, owner, "sending")
        try:
            message_id = self.api.send_message(message.chat.id, "Welcome to HighGround. Shop onboarding is not connected yet.")
        except TelegramSendError as error:
            state = "uncertain" if error.uncertain else "retryable"
            self.inbox.transition(update.update_id, owner, state)
            if error.uncertain:
                return "uncertain"
            raise WebhookRetry() from None
        self.inbox.transition(update.update_id, owner, "done", message_id=message_id)
        return "done"
