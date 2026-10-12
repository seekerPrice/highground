"""HighGround liveness and durable Telegram webhook."""
import hmac
import json
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from api.config import Settings, load_settings
from api.telegram_webhook import TelegramHandler, Update


def create_app(settings: Settings | None = None, handler: TelegramHandler | None = None) -> FastAPI:
    application = FastAPI(title="HighGround API")
    application.state.telegram_handler = handler

    @application.get("/healthz")
    def healthz() -> dict[str, Literal["ok"]]:
        return {"status": "ok"}

    @application.post("/telegram/webhook")
    async def webhook(request: Request) -> dict[str, bool]:
        configuration = settings or load_settings()
        secret = configuration.telegram_webhook_secret
        if not secret:
            raise HTTPException(503, "Telegram webhook is not configured")
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(supplied.encode(), secret.encode()):
            raise HTTPException(403, "Invalid webhook secret")
        chunks = bytearray()
        async for chunk in request.stream():
            chunks.extend(chunk)
            if len(chunks) > 256_000:
                raise HTTPException(413, "Update too large")
        body = bytes(chunks)
        try:
            payload = json.loads(body)
            update = Update.model_validate(payload)
        except (ValueError, ValidationError, RecursionError):
            raise HTTPException(400, "Invalid Telegram update") from None
        try:
            active = application.state.telegram_handler
            if active is None:
                from api.telegram_inbox import FirestoreInbox
                from api.tools.firestore import create_firestore_client
                from api.tools.telegram import TelegramAPI

                active = TelegramHandler(FirestoreInbox(create_firestore_client(configuration)), TelegramAPI(configuration.telegram_bot_token))
                application.state.telegram_handler = active
            await run_in_threadpool(active.handle, update, payload)
        except Exception:
            # Private payloads, token-bearing URLs and SDK errors stay out of responses.
            raise HTTPException(503, "Webhook processing unavailable; retry later") from None
        return {"ok": True}

    return application


app = create_app()
