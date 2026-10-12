"""Bounded Bot API calls with sanitized errors."""
from typing import Any
import logging
import re

import httpx


class _RedactBotURL(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = re.sub(r"/bot[^/\s]+", "/bot[redacted]", record.getMessage())
        record.args = ()
        return True


# HTTPX emits full request URLs at INFO; Bot API authentication is in that URL.
for _logger in ("httpx", "httpcore.connection", "httpcore.http11", "httpcore.http2", "httpcore.proxy"):
    logging.getLogger(_logger).addFilter(_RedactBotURL())


class TelegramSendError(Exception):
    def __init__(self, *, uncertain: bool) -> None:
        self.uncertain = uncertain
        super().__init__("Telegram send outcome uncertain" if uncertain else "Telegram rejected send")


class TelegramAPI:
    def __init__(self, token: str, transport: httpx.BaseTransport | None = None) -> None:
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self._token = token
        self._transport = transport

    def send_message(self, chat_id: int, text: str) -> int:
        # Never expose raw HTTP exceptions: their URLs contain the bot token.
        try:
            with httpx.Client(transport=self._transport, timeout=15) as client:
                response = client.post(
                    f"https://api.telegram.org/bot{self._token}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                )
            body: Any = response.json()
            if not isinstance(body, dict) or not isinstance(body.get("ok"), bool):
                raise TelegramSendError(uncertain=True)
            if body["ok"] is False:
                raise TelegramSendError(uncertain=False)
            message = body.get("result")
            if not response.is_success or not isinstance(message, dict):
                raise TelegramSendError(uncertain=True)
            message_id = message.get("message_id")
            if type(message_id) is not int:
                raise TelegramSendError(uncertain=True)
            return message_id
        except httpx.ConnectError:
            raise TelegramSendError(uncertain=False) from None
        except (httpx.HTTPError, ValueError):
            raise TelegramSendError(uncertain=True) from None
