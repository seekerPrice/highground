import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
import re
from uuid import uuid4

from google.auth.credentials import AnonymousCredentials
from google.cloud import firestore
import httpx
import pytest

from api.agents.sessions import create_session_service, session_user_id
from api.config import Settings
from api.main import create_app
from api.onboarding import Onboarding
from api.onboarding_store import OnboardingStore, InvitationInvalid
from api.telegram_inbox import FirestoreInbox
from api.telegram_webhook import TelegramHandler
from api.tools.firestore import create_async_firestore_client, close_async_firestore_client
from api.tools.geocoding import Geocoder
from api.tools.telegram import TelegramAPI

pytestmark = pytest.mark.skipif(not os.environ.get("FIRESTORE_EMULATOR_HOST"), reason="actual local emulator required")
SETTINGS = Settings(gcp_project="highground-onboarding-tests", hash_salt="synthetic-salt", telegram_webhook_secret="synthetic-secret", telegram_bot_username="test_highground_bot", geocoding_user_agent="HighGround-test/1.0 (https://example.com)")
HEADERS = {"X-Telegram-Bot-Api-Secret-Token": "synthetic-secret"}


class Harness:
    async def initialize(self):
        assert os.environ["FIRESTORE_EMULATOR_HOST"] == "127.0.0.1:8787"
        self.prefix = "onboarding_test_" + uuid4().hex + "_"
        self.client = firestore.Client(project=SETTINGS.gcp_project, credentials=AnonymousCredentials())
        self.async_clients = []
        self.sessions = []
        self.store = OnboardingStore(self.client, prefix=self.prefix)
        self.calls = []
        self.methods = []
        self.update_id = 0
        self.chat_ids = set()
        self.dates = {}
        self.reconstruct()

    def reconstruct(self, geocode_transport=None):
        async_client = create_async_firestore_client(SETTINGS)
        self.async_clients.append(async_client)
        sessions = create_session_service(SETTINGS, root_collection=self.prefix + "adk", client=async_client)
        self.sessions.append(sessions)
        self.geocoder = Geocoder(self.store, user_agent=SETTINGS.geocoding_user_agent, transport=geocode_transport)
        onboarding = Onboarding(self.store, sessions, hash_salt=SETTINGS.hash_salt, bot_username=SETTINGS.telegram_bot_username, geocoder=self.geocoder)
        def transport(request):
            self.calls.append(json.loads(request.content))
            self.methods.append(request.url.path.rsplit("/", 1)[1])
            return httpx.Response(200, json={"ok": True, "result": {"message_id": len(self.calls)}})
        handler = TelegramHandler(FirestoreInbox(self.client, self.prefix + "inbox"), TelegramAPI("synthetic-token", httpx.MockTransport(transport)), onboarding)
        self.onboarding = onboarding
        self.app = create_app(SETTINGS, handler)

    async def send(self, value=None, *, chat_id=9, location=None, update_id=None, date=None, expected_status=200):
        self.chat_ids.add(chat_id)
        if update_id is None:
            self.update_id += 1
            update_id = self.update_id
        message = {"message_id": update_id, "chat": {"id": chat_id, "type": "private"}}
        if date is None:
            date = self.dates.setdefault(update_id, int(datetime.now(timezone.utc).timestamp()))
        message["date"] = date
        if value is not None:
            message["text"] = value
        if location is not None:
            message["location"] = location
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test") as client:
            response = await client.post("/telegram/webhook", headers=HEADERS, json={"update_id": update_id, "message": message})
        assert response.status_code == expected_status, response.text
        return self.calls[-1].get("text", self.calls[-1].get("address", "")) if self.calls else ""

    async def state(self, chat_id=9):
        session = await self.sessions[-1].get_session(app_name="highground_onboarding", user_id=session_user_id(chat_id, SETTINGS.hash_salt), session_id="registration")
        return session.state["onboarding"]

    async def owner_flow(self, *, language="en", vehicle=True):
        await self.send("/start")
        await self.send(language)
        await self.send(location={"latitude": 3.028, "longitude": 101.725})
        await self.send("Synthetic Demo Shop")
        await self.send("mini-market")
        await self.send("ground")
        await self.send("yes" if vehicle else "no")
        if vehicle:
            await self.send("van")
        return await self.send("skip")

    async def close(self):
        for chat_id in self.chat_ids:
            await self.sessions[-1].delete_session(app_name="highground_onboarding", user_id=session_user_id(chat_id, SETTINGS.hash_salt), session_id="registration")
        # Only this unique test namespace is cleaned; no emulator reset.
        for collection in self.client.collections():
            if collection.id.startswith(self.prefix):
                for document in collection.stream():
                    document.reference.delete()
        for client in self.async_clients:
            await close_async_firestore_client(client)
        self.client.close()


def test_public_owner_flow_restart_invalid_input_and_completion_replay():
    async def run():
        h = Harness()
        await h.initialize()
        try:
            await h.send("/start")
            await h.send("zh")
            await h.send("not a shared location")
            assert (await h.state())["stage"] == "location"
            await h.send(location={"latitude": 3.028, "longitude": 101.725})
            h.reconstruct()
            await h.send("/start")
            assert (await h.state())["stage"] == "name"
            await h.send("x")
            assert (await h.state())["stage"] == "name"
            for value in ["Synthetic Demo Shop", "mini-market", "ground", "yes", "van", "skip"]:
                await h.send(value)
            last_update = h.update_id
            count = len(h.calls)
            h.reconstruct()
            await h.send("skip", update_id=last_update)
            assert len(h.calls) == count
            rows = list(h.store.collection("shops").stream())
            assert len(rows) == 1
            shop = rows[0].to_dict()
            assert shop["risk_score"] == 60 and shop["risk_score_provisional"] is True
            assert shop["risk_score_missing"] == ["inventory", "river_or_past_event_exposure"]
            assert shop["is_demo"] is False  # Never infer simulation from a name.
            assert shop["recipients"] == [{"telegram_chat_id": 9, "language": "zh", "role": "owner"}]
            await h.send("/start")
            assert len(list(h.store.collection("shops").stream())) == 1
            for document in h.store.collection("inbox").stream():
                assert "payload" not in document.to_dict()
        finally:
            await h.close()
    asyncio.run(run())


def test_worker_self_start_consent_language_single_use_and_hashed_token():
    async def run():
        h = Harness()
        await h.initialize()
        try:
            await h.owner_flow()
            invitation_text = await h.send("/invite")
            token = re.search(r"start=join_([A-Za-z0-9_-]{32})", invitation_text).group(1)
            digest = h.store.invitation_digest(token)
            assert token not in json.dumps([d.to_dict() for d in h.store.collection("invitations").stream()], default=str)
            assert token not in json.dumps((await h.state()), default=str)
            await h.send("/start join_" + token)
            assert (await h.state())["stage"] == "done"
            await h.send("/start join_" + token, chat_id=10)
            await h.send("ms", chat_id=10)
            shop_id = (await h.state())["shop_id"]
            assert len(h.store.get_shop(shop_id)["recipients"]) == 1
            h.reconstruct()
            await h.send("yes", chat_id=10)
            consent_update = h.update_id
            assert h.store.get_shop(shop_id)["recipients"][1] == {"telegram_chat_id": 10, "language": "ms", "role": "worker"}
            # Same operation may recover after domain commit and before ADK append.
            recovered = h.store.join(digest, 10, session_user_id(10, SETTINGS.hash_salt), "ms", consent_update)
            assert recovered["shop_id"] == shop_id
            with pytest.raises(InvitationInvalid):
                h.store.join(digest, 10, session_user_id(10, SETTINGS.hash_salt), "ms", consent_update + 1)
            with pytest.raises(InvitationInvalid):
                h.store.join(digest, 11, session_user_id(11, SETTINGS.hash_salt), "en", consent_update)
            await h.send("/start join_" + token, chat_id=11)
            assert len(h.store.get_shop(shop_id)["recipients"]) == 2
        finally:
            await h.close()
    asyncio.run(run())


def test_worker_decline_and_expired_invitation_do_not_add_recipient():
    async def run():
        h = Harness()
        await h.initialize()
        try:
            await h.owner_flow(vehicle=False)
            invitation = await h.send("/invite")
            token = re.search(r"start=join_([A-Za-z0-9_-]{32})", invitation).group(1)
            await h.send("/start join_" + token, chat_id=10)
            await h.send("en", chat_id=10)
            await h.send("no", chat_id=10)
            shop_id = (await h.state())["shop_id"]
            assert len(h.store.get_shop(shop_id)["recipients"]) == 1
            h.store.collection("invitations").document(h.store.invitation_digest(token)).update({"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
            await h.send("/start join_" + token, chat_id=11)
            assert len(h.store.get_shop(shop_id)["recipients"]) == 1
            assert h.store.get_shop(shop_id)["risk_score"] == 40
        finally:
            await h.close()
    asyncio.run(run())


def test_geocoder_candidate_requires_confirmation_and_handles_failure():
    async def run():
        h = Harness()
        await h.initialize()
        requests = []
        def geocode(request):
            requests.append(request)
            return httpx.Response(200, json=[{"lat": "3.028", "lon": "101.725", "display_name": "Synthetic public shop address"}])
        try:
            h.reconstruct(httpx.MockTransport(geocode))
            await h.send("/start")
            await h.send("en")
            await h.send("/address Synthetic public shop address")
            state = await h.state()
            assert state["stage"] == "confirm_location" and "lat" not in state
            assert list(h.store.collection("shops").stream()) == []
            assert h.methods[-1] == "sendVenue"
            assert "OpenStreetMap" in h.calls[-1]["address"]
            assert h.calls[-1]["latitude"] == 3.028 and h.calls[-1]["longitude"] == 101.725
            assert len(h.calls[-1]["reply_markup"]["keyboard"]) == 2
            assert requests[0].headers["User-Agent"] == SETTINGS.geocoding_user_agent
            await h.send("reject")
            assert (await h.state())["stage"] == "location"
            await h.send("/address Synthetic public shop address")  # Cached, no repeated search.
            assert len(requests) == 1
            await h.send("confirm")
            assert (await h.state())["lat"] == 3.028
            failures = []
            def unavailable(request):
                failures.append(request)
                return httpx.Response(503)
            h.reconstruct(httpx.MockTransport(unavailable))
            h.store.collection("geocode_gate").document("application").update({"next_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
            assert await h.geocoder.search("A different synthetic shop") is None
            assert len(failures) == 1
        finally:
            await h.close()
    asyncio.run(run())


def test_invalid_location_never_advances_or_persists_coordinates():
    async def run():
        h = Harness()
        await h.initialize()
        try:
            await h.send("/start")
            await h.send("en")
            for latitude in [91, float("nan")]:
                body = {"update_id": 99, "message": {"message_id": 99, "chat": {"id": 9, "type": "private"}, "location": {"latitude": latitude, "longitude": 101}}}
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app), base_url="http://test") as client:
                    if latitude != latitude:
                        response = await client.post("/telegram/webhook", headers=HEADERS, content=json.dumps(body))
                    else:
                        response = await client.post("/telegram/webhook", headers=HEADERS, json=body)
                assert response.status_code == 400
            assert (await h.state())["stage"] == "location"
        finally:
            await h.close()
    asyncio.run(run())


@pytest.mark.parametrize("rows", [[], [{"lat": "3", "lon": "101", "display_name": "One"}, {"lat": "4", "lon": "102", "display_name": "Two"}], [{"lat": "nan", "lon": "101", "display_name": "Invalid"}], [{"lat": True, "lon": "101", "display_name": "Invalid"}]])
def test_geocoder_ambiguous_or_invalid_result_is_unavailable(rows):
    async def run():
        h = Harness()
        await h.initialize()
        try:
            h.reconstruct(httpx.MockTransport(lambda _: httpx.Response(200, json=rows)))
            assert await h.geocoder.search("Synthetic public business") is None
            assert list(h.store.collection("geocode_cache").stream()) == []
        finally:
            await h.close()
    asyncio.run(run())


def test_invite_completion_includes_registration_and_provisional_risk_summary():
    async def run():
        h = Harness()
        await h.initialize()
        try:
            for value in ["/start", "en"]:
                await h.send(value)
            await h.send(location={"latitude": 3.028, "longitude": 101.725})
            for value in ["Synthetic Shop", "eatery", "ground", "no"]:
                await h.send(value)
            response = await h.send("invite")
            assert "Provisional risk score: 40/100" in response
            assert "unknown" in response and "start=join_" in response
            assert (await h.state())["stage"] == "done"
            token = re.search(r"start=join_([A-Za-z0-9_-]{32})", response).group(1)
            assert token not in json.dumps(await h.state())
        finally:
            await h.close()
    asyncio.run(run())



def test_lower_update_id_is_accepted_after_documented_idle_reset():
    async def run():
        h = Harness()
        await h.initialize()
        try:
            h.update_id = 100
            await h.owner_flow()
            initial = await h.state()
            await h.send("/invite", update_id=50)
            assert "start=join_" not in h.calls[-1]["text"]
            h.onboarding.clock = lambda: initial["last_update_at"] + 8 * 24 * 60 * 60
            await h.send("/invite", update_id=51, date=int(initial["last_update_at"]) + 8 * 24 * 60 * 60)
            assert "start=join_" in h.calls[-1]["text"]
            assert (await h.state())["last_update_id"] == 51
            count = len(h.calls)
            await h.send("/invite", update_id=51, date=int(initial["last_update_at"]) + 8 * 24 * 60 * 60)
            assert len(h.calls) == count
            # A new dated message may legitimately reuse the randomized ID
            # after another week; its operation identity is not the old claim.
            h.onboarding.clock = lambda: initial["last_update_at"] + 16 * 24 * 60 * 60
            await h.send("/invite", update_id=51, date=int(initial["last_update_at"]) + 16 * 24 * 60 * 60)
            assert len(h.calls) == count + 1
            assert "start=join_" in h.calls[-1]["text"]
        finally:
            await h.close()
    asyncio.run(run())


def test_worker_recovers_after_domain_commit_before_session_append():
    async def run():
        h = Harness()
        await h.initialize()
        try:
            await h.owner_flow()
            response = await h.send("/invite")
            token = re.search(r"start=join_([A-Za-z0-9_-]{32})", response).group(1)
            await h.send("/start join_" + token, chat_id=10)
            await h.send("en", chat_id=10)
            original = h.sessions[-1].append_event
            failed = False
            async def fail_once(session, event):
                nonlocal failed
                if event.actions.state_delta["onboarding"]["stage"] == "worker_done" and not failed:
                    failed = True
                    raise RuntimeError("Synthetic failure after join commit")
                return await original(session, event)
            h.sessions[-1].append_event = fail_once
            before = len(h.calls)
            await h.send("yes", chat_id=10, expected_status=503)
            retry_id = h.update_id
            assert len(h.calls) == before
            assert (await h.state(10))["stage"] == "worker_confirm"
            await h.send("yes", chat_id=10, update_id=retry_id)
            assert (await h.state(10))["stage"] == "worker_done"
            shop = h.store.get_shop((await h.state())["shop_id"])
            assert len(shop["recipients"]) == 2
        finally:
            await h.close()
    asyncio.run(run())


@pytest.mark.parametrize("timestamp", [None, True, -1, "today"])
def test_onboarding_missing_or_malformed_timestamp_rejected(timestamp):
    async def run():
        h = Harness()
        await h.initialize()
        try:
            message = {"message_id": 1, "chat": {"id": 9, "type": "private"}, "text": "/start"}
            if timestamp is not None:
                message["date"] = timestamp
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=h.app), base_url="http://test") as client:
                response = await client.post("/telegram/webhook", headers=HEADERS, json={"update_id": 1, "message": message})
            assert response.status_code == 400
            assert list(h.store.collection("inbox").stream()) == []
        finally:
            await h.close()
    asyncio.run(run())
