"""HighGround liveness and durable Telegram webhook."""
import hmac
import json
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from api.config import Settings, load_settings
from api.telegram_webhook import TelegramHandler, Update


def create_app(settings: Settings | None = None, handler: TelegramHandler | None = None, dispatch_service=None) -> FastAPI:
    application = FastAPI(title="HighGround API")
    application.state.telegram_handler = handler
    from api.dispatch_router import create_dispatch_router
    application.include_router(create_dispatch_router(settings or load_settings, dispatch_service))

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
        active = application.state.telegram_handler
        if update.message is not None and update.message.date is None and (active is None or active.onboarding is not None or active.photos is not None):
            raise HTTPException(400, "Telegram message timestamp is required")
        try:
            active = application.state.telegram_handler
            if active is None:
                from api.telegram_inbox import FirestoreInbox
                from api.tools.firestore import create_firestore_client
                from api.tools.telegram import TelegramAPI

                from api.agents.sessions import create_session_service
                from api.onboarding import Onboarding
                from api.onboarding_store import OnboardingStore
                from api.tools.geocoding import Geocoder

                client = create_firestore_client(configuration)
                store = OnboardingStore(client)
                onboarding = Onboarding(store, create_session_service(configuration), hash_salt=configuration.hash_salt, bot_username=configuration.telegram_bot_username, geocoder=Geocoder(store, user_agent=configuration.geocoding_user_agent, base_url=configuration.geocoding_base_url))
                from api.vehicle_confirmations import VehicleActionStore, VehicleConfirmationService
                from api.tools.cloud_events import create_event_sinks

                # Analytics clients remain lazy until a completion actually needs a sink.
                class ConfirmationSinks:
                    def __init__(self):
                        self.active = None
                    def insert_confirmation(self, record):
                        if self.active is None:
                            self.active = create_event_sinks(configuration)
                        self.active.insert_confirmation(record)
                confirmations = VehicleConfirmationService(VehicleActionStore(client), ConfirmationSinks(), hash_salt=configuration.hash_salt)
                from api.photo_reports import LazyPhotoReportService
                photos = LazyPhotoReportService(configuration, dispatch_service=dispatch_service)
                active = TelegramHandler(FirestoreInbox(client), TelegramAPI(configuration.telegram_bot_token), onboarding, confirmations, photos)
                application.state.telegram_handler = active
            await active.handle(update)
        except Exception:
            # Private payloads, token-bearing URLs and SDK errors stay out of responses.
            raise HTTPException(503, "Webhook processing unavailable; retry later") from None
        return {"ok": True}

    return application


app = create_app()
