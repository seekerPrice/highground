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

    def send_message(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> int:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text, "link_preview_options": {"is_disabled": True}}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._send("sendMessage", payload)

    def send_photo(self, chat_id: int, data: bytes, caption: str) -> int:
        if not isinstance(data,bytes) or not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data)>10_000_000:
            raise ValueError('Card must be a PNG photo of at most10MB')
        if len(caption)>1024:raise ValueError('Photo caption must fit Telegram limit')
        return self._send('sendPhoto',{'chat_id':str(chat_id),'caption':caption},photo=data)

    def send_document(self,chat_id:int,data:bytes,mime_type:str,filename:str)->int:
        if not isinstance(data,bytes) or not 0<len(data)<=20_000_000 or mime_type not in ('application/pdf','image/jpeg','image/png','image/webp'):raise ValueError('Bounded private policy document required')
        if not re.fullmatch(r'policy-page-[1-5]\.(pdf|jpg|png|webp)',filename):raise ValueError('Safe policy filename required')
        return self._send('sendDocument',{'chat_id':str(chat_id)},document=(filename,data,mime_type))

    def send_venue(self, chat_id: int, latitude: float, longitude: float, title: str, address: str, reply_markup: dict[str, Any] | None = None) -> int:
        payload: dict[str, Any] = {"chat_id": chat_id, "latitude": latitude, "longitude": longitude, "title": title, "address": address}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._send("sendVenue", payload)

    def answer_callback_query(self, callback_query_id: str, text: str) -> None:
        if not 0 <= len(text) <= 200:
            raise ValueError('Callback feedback must fit Telegram limit')
        try:
            with httpx.Client(transport=self._transport, timeout=5) as client:
                response = client.post(f'https://api.telegram.org/bot{self._token}/answerCallbackQuery',
                                       json={'callback_query_id': callback_query_id, 'text': text})
            body = response.json()
            if not response.is_success or not isinstance(body, dict) or body.get('ok') is not True or body.get('result') is not True:
                raise TelegramSendError(uncertain=True)
        except (httpx.HTTPError, ValueError):
            raise TelegramSendError(uncertain=True) from None

    def _send(self, method: str, payload: dict[str, Any], *, photo: bytes | None = None, document: tuple[str,bytes,str] | None = None) -> int:
        # Never expose raw HTTP exceptions: their URLs contain the bot token.
        try:
            with httpx.Client(transport=self._transport, timeout=15) as client:
                url=f"https://api.telegram.org/bot{self._token}/{method}"
                if document is not None:response=client.post(url,data=payload,files={'document':document})
                elif photo is not None:response=client.post(url,data=payload,files={'photo':('offline-card.png',photo,'image/png')})
                else:response=client.post(url,json=payload)
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
