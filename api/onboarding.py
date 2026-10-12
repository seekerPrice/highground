"""Deterministic onboarding persisted through ADK's Firestore session service."""
from dataclasses import dataclass
import re
from typing import Any, Callable
import time

from google.adk.events import Event, EventActions
from google.adk.errors.already_exists_error import AlreadyExistsError
from google.adk.integrations.firestore.firestore_session_service import FirestoreSessionService
from starlette.concurrency import run_in_threadpool

from api.agents.sessions import session_user_id
from api.i18n import LANGUAGES, catalog, text
from api.onboarding_store import OnboardingStore, InvitationInvalid
from api.tools.geocoding import Geocoder

LANGUAGE_LABELS = {"en": "English (en)", "ms": "Bahasa Melayu (ms)", "zh": "中文 (zh)", "ta": "தமிழ் (ta)", "bn": "বাংলা (bn)", "ne": "नेपाली (ne)", "my": "မြန်မာ (my)", "id": "Bahasa Indonesia (id)"}
CHOICES = {"floor": ["ground", "upper"], "vehicle": ["yes", "no"], "vehicle_type": ["car", "van", "lorry", "motorcycle"], "worker": ["invite", "skip"], "confirm_location": ["confirm", "reject"], "worker_confirm": ["yes", "no"]}
PROMPTS = {"language": "choose_language", "worker_language": "choose_language", "location": "location_prompt", "confirm_location": "address_confirm", "name": "shop_name_prompt", "type": "shop_type_prompt", "floor": "floor_prompt", "vehicle": "vehicle_prompt", "vehicle_type": "vehicle_type_prompt", "worker": "worker_prompt", "worker_confirm": "join_prompt"}


@dataclass(frozen=True)
class Reply:
    text: str
    reply_markup: dict[str, Any]
    venue: dict[str, Any] | None = None


class Onboarding:
    def __init__(self, store: OnboardingStore, sessions: FirestoreSessionService, *, hash_salt: str, bot_username: str, geocoder: Geocoder, clock: Callable[[], float] = time.time) -> None:
        self.store = store
        self.sessions = sessions
        self.hash_salt = hash_salt
        self.bot_username = bot_username
        self.geocoder = geocoder
        self.clock = clock

    def reply(self, state: dict[str, Any], key: str | None = None, **values: object) -> Reply:
        language = state.get("language", "en")
        stage = state["stage"]
        key = key or PROMPTS.get(stage, "invalid_input")
        if key == "address_confirm":
            values = {"address": state["candidate"]["address_text"]}
        if key == "join_prompt":
            values = {"shop_name": state["join_shop_name"]}
        rendered = text(language, key, **values)
        if not catalog(language)["_reviewed"]:
            rendered += "\n" + text(language, "translation_notice")
        if stage in ("language", "worker_language"):
            labels = list(LANGUAGE_LABELS.values())
        else:
            labels = [text(language, value) for value in CHOICES.get(stage, [])]
        if stage == "location":
            markup = {"keyboard": [[{"text": "📍", "request_location": True}]], "resize_keyboard": True}
        elif labels:
            markup = {"keyboard": [[{"text": label}] for label in labels], "resize_keyboard": True, "one_time_keyboard": True}
        else:
            markup = {"remove_keyboard": True}
        venue = {"latitude": state["candidate"]["lat"], "longitude": state["candidate"]["lng"], "title": text(language, "confirm"), "address": rendered} if stage == "confirm_location" else None
        return Reply(rendered, markup, venue)

    async def process(self, chat_id: int, update_id: int, message_text: str | None, location: dict[str, float] | None, message_date: int | None = None) -> Reply:
        if message_date is None:
            raise ValueError("Telegram message timestamp is required for onboarding")
        identity = session_user_id(chat_id, self.hash_salt)
        owner = await run_in_threadpool(self.store.acquire, identity)
        try:
            kwargs = {"app_name": "highground_onboarding", "user_id": identity, "session_id": "registration"}
            session = await self.sessions.get_session(**kwargs)
            if session is None:
                try:
                    session = await self.sessions.create_session(**kwargs, state={"onboarding": {"stage": "language", "language": "en"}})
                except AlreadyExistsError:
                    session = await self.sessions.get_session(**kwargs)
            state = dict(session.state["onboarding"])
            # Process a given update at most once in conversation state. Delivery
            # is a separate inbox operation; replay uses the committed reply facts.
            now = self.clock()
            idle_reset = now - state.get("last_update_at", now) >= 7 * 24 * 60 * 60
            if message_date is not None and state.get("last_message_date") is not None and message_date <= state["last_message_date"]:
                idle_reset = False
            if update_id <= state.get("last_update_id", -1) and not idle_reset:
                key = state.get("last_reply_key")
                return self.reply(state, key, **state.get("last_reply_values", {}))
            reply, key, values = await self.transition(state, chat_id, identity, update_id, (message_text or "").strip(), location)
            state.update(last_update_id=update_id, last_update_at=now, last_message_date=message_date, last_reply_key=key, last_reply_values=values)
            await self.sessions.append_event(session, Event(author="highground_coordinator", invocation_id=f"onboarding-{update_id}", actions=EventActions(state_delta={"onboarding": state})))
            return reply
        finally:
            await run_in_threadpool(self.store.release, identity, owner)

    async def transition(self, state: dict[str, Any], chat_id: int, identity: str, update_id: int, value: str, location: dict[str, float] | None) -> tuple[Reply, str | None, dict[str, object]]:
        stage, language = state["stage"], state.get("language", "en")
        key = None
        values: dict[str, object] = {}
        words = value.split()
        if words and words[0] == "/start" and len(words) == 2 and words[1].startswith("join_"):
            if stage == "done":
                shop = await run_in_threadpool(self.store.get_shop, state["shop_id"])
                return self.reply(state, "resume", shop_name=shop["shop_name"]), "resume", {"shop_name": shop["shop_name"]}
            token = words[1][5:]
            if not re.fullmatch(r"[A-Za-z0-9_-]{32}", token):
                return self.reply(state, "join_expired"), "join_expired", {}
            digest = self.store.invitation_digest(token)
            try:
                shop = await run_in_threadpool(self.store.invitation_shop, digest)
            except InvitationInvalid:
                return self.reply(state, "join_expired"), "join_expired", {}
            state.clear()
            state.update(stage="worker_language", language="en", invite_digest=digest, join_shop_name=shop["shop_name"])
        elif value == "/start":
            if stage in ("done", "worker_done"):
                shop = await run_in_threadpool(self.store.get_shop, state["shop_id"])
                key, values = "resume", {"shop_name": shop["shop_name"]}
        elif value == "/invite" and stage == "done":
            return await self.invite(state, chat_id)
        elif stage in ("language", "worker_language"):
            code = next((code for code, label in LANGUAGE_LABELS.items() if value in (code, label)), None)
            if code:
                state.update(language=code, stage="worker_confirm" if stage == "worker_language" else "location")
            else:
                key = "invalid_input"
        elif stage == "location":
            if location:
                state.update(**location, address_text="", stage="name")
            elif value.startswith("/address "):
                candidate = await self.geocoder.search(value[len("/address "):].strip())
                if candidate:
                    state.update(candidate=candidate, stage="confirm_location")
                else:
                    key = "address_unavailable"
            else:
                key = "location_invalid"
        elif stage in ("name", "type"):
            limit = 100 if stage == "name" else 80
            if 2 <= len(value) <= limit and not any(ord(char) < 32 for char in value):
                state["shop_name" if stage == "name" else "shop_type"] = value
                state["stage"] = "type" if stage == "name" else "floor"
            else:
                key = "invalid_input"
        elif stage in CHOICES:
            choice = next((choice for choice in CHOICES[stage] if value in (choice, text(language, choice))), None)
            if choice is None:
                key = "invalid_input"
            elif stage == "confirm_location":
                candidate = state.pop("candidate")
                if choice == "confirm":
                    state.update(**candidate, stage="name")
                else:
                    state["stage"] = "location"
            elif stage == "floor":
                state.update(floor=choice, stage="vehicle")
            elif stage == "vehicle":
                state.update(has_vehicle=choice == "yes", stage="vehicle_type" if choice == "yes" else "worker")
            elif stage == "vehicle_type":
                state.update(vehicle_type=choice, stage="worker")
            elif stage == "worker":
                shop_id = await run_in_threadpool(self.store.save_shop, identity, chat_id, state)
                shop = await run_in_threadpool(self.store.get_shop, shop_id)
                state.clear()
                state.update(stage="done", language=language, shop_id=shop_id)
                key, values = "registered", {"shop_name": shop["shop_name"], "score": shop["risk_score"]}
                if choice == "invite":
                    invitation, _, _ = await self.invite(state, chat_id)
                    summary = self.reply(state, key, **values)
                    return Reply(summary.text + "\n\n" + invitation.text, invitation.reply_markup), key, values
            elif stage == "worker_confirm":
                if choice == "no":
                    state.clear()
                    state.update(stage="language", language=language)
                    key = "join_declined"
                else:
                    try:
                        shop = await run_in_threadpool(self.store.join, state["invite_digest"], chat_id, identity, language, update_id)
                    except InvitationInvalid:
                        key = "join_expired"
                    else:
                        state.clear()
                        state.update(stage="worker_done", language=language, shop_id=shop["shop_id"])
                        key, values = "joined", {"shop_name": shop["shop_name"]}
        else:
            key = "invite_again" if stage == "done" else "invalid_input"
        return self.reply(state, key, **values), key, values

    async def invite(self, state: dict[str, Any], chat_id: int) -> tuple[Reply, str, dict[str, object]]:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", self.bot_username):
            return self.reply(state, "invite_unavailable"), "invite_unavailable", {}
        try:
            token = await run_in_threadpool(self.store.create_invitation, state["shop_id"], chat_id)
        except InvitationInvalid:
            return self.reply(state, "invite_unavailable"), "invite_unavailable", {}
        reply = self.reply(state, "invite_link", link=f"https://t.me/{self.bot_username}?start=join_{token}")
        # The random token is never stored in session state, events or inbox.
        return reply, "invite_again", {}
