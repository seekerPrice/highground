import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os
from uuid import uuid4

import asyncio
from typing import Any

from fastapi import FastAPI
from google.cloud import firestore
from google.auth.credentials import AnonymousCredentials
import httpx
import pytest

from api.config import Settings, load_settings
from api.main import create_app
from api.telegram_inbox import FirestoreInbox
from api.telegram_webhook import TelegramHandler
from api.tools.telegram import TelegramAPI

def request(app: FastAPI, method: str, url: str, **kwargs: Any) -> httpx.Response:
    async def send() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, url, **kwargs)
    return asyncio.run(send())


PAYLOAD = {"update_id": 123, "message": {"message_id": 8, "chat": {"id": 9, "type": "private"}, "text": "/start"}}
SETTINGS = Settings(telegram_webhook_secret="test-secret")
HEADERS = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}


@pytest.fixture
def inbox():
    host = os.getenv("FIRESTORE_EMULATOR_HOST")
    if not host:
        pytest.skip("Set FIRESTORE_EMULATOR_HOST for actual persistence tests")
    if host != "127.0.0.1:8787":
        pytest.fail("These tests require the dedicated loopback emulator")
    client = firestore.Client(project="highground-telegram-tests", credentials=AnonymousCredentials())
    store = FirestoreInbox(client, "telegram_tests_" + uuid4().hex)
    yield store
    for doc in client.collection(store.collection).stream():
        doc.reference.delete()
    client.close()


def make_handler(inbox, calls, result=None):
    def transport(request):
        calls.append(json.loads(request.content))
        if result == "uncertain":
            raise httpx.ReadTimeout("private token URL", request=request)
        if result == "reject":
            return httpx.Response(429, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 100}})
    return TelegramHandler(inbox, TelegramAPI("test-token", httpx.MockTransport(transport)))


@pytest.mark.parametrize("headers", [{}, {"X-Telegram-Bot-Api-Secret-Token": "wrong"}])
def test_secret_rejected_before_work(headers):
    app = create_app(SETTINGS)
    response = request(app, "POST", "/telegram/webhook", headers=headers, json=PAYLOAD)
    assert response.status_code == 403
    assert "test-secret" not in response.text


def test_health_independent_of_config():
    app = create_app(Settings())
    assert request(app, "GET", "/healthz").json() == {"status": "ok"}
    assert request(app, "POST", "/telegram/webhook", json=PAYLOAD).status_code == 503


@pytest.mark.parametrize("payload", [{}, {"update_id": True}, {"update_id": -1}, {"update_id": "123"}, {"update_id": 1, "message": {"chat": {"id": "private"}}}])
def test_invalid_updates_sanitized(payload):
    app = create_app(SETTINGS)
    response = request(app, "POST", "/telegram/webhook", headers=HEADERS, json=payload)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Telegram update"}


def test_start_and_restart_dedupe(inbox):
    calls = []
    for _ in range(2):
        reconstructed = FirestoreInbox(inbox.client, inbox.collection)
        app = create_app(SETTINGS, make_handler(reconstructed, calls))
        assert request(app, "POST", "/telegram/webhook", headers=HEADERS, json=PAYLOAD).status_code == 200
    assert len(calls) == 1
    assert calls[0]["chat_id"] == 9
    assert "HighGround" in calls[0]["text"]
    assert inbox.client.collection(inbox.collection).document("123").get().to_dict()["status"] == "done"


def test_concurrent_claim_has_one_owner(inbox):
    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(lambda _: inbox.claim(123)[0], range(2)))
    assert sorted(claims) == ["busy", "claimed"]


@pytest.mark.parametrize("payload", [{"update_id": 123}, {**PAYLOAD, "message": {**PAYLOAD["message"], "text": " "}}])
def test_unsupported_update_durable_without_send(inbox, payload):
    calls = []
    handler = make_handler(inbox, calls)
    app = create_app(SETTINGS, handler)
    assert request(app, "POST", "/telegram/webhook", headers=HEADERS, json=payload).status_code == 200
    assert calls == []
    state = inbox.client.collection(inbox.collection).document("123").get().to_dict()
    assert state["status"] == "done"
    assert state["outcome"] == "unsupported"


def test_uncertain_send_retained_and_not_repeated(inbox):
    calls = []
    app = create_app(SETTINGS, make_handler(inbox, calls, "uncertain"))
    assert request(app, "POST", "/telegram/webhook", headers=HEADERS, json=PAYLOAD).status_code == 200
    reconstructed = FirestoreInbox(inbox.client, inbox.collection)
    app = create_app(SETTINGS, make_handler(reconstructed, calls))
    assert request(app, "POST", "/telegram/webhook", headers=HEADERS, json=PAYLOAD).status_code == 200
    assert len(calls) == 1
    assert inbox.client.collection(inbox.collection).document("123").get().to_dict()["status"] == "uncertain"


def test_definite_rejection_can_retry(inbox):
    calls = []
    app = create_app(SETTINGS, make_handler(inbox, calls, "reject"))
    response = request(app, "POST", "/telegram/webhook", headers=HEADERS, json=PAYLOAD)
    assert response.status_code == 503
    assert "test-token" not in response.text
    app = create_app(SETTINGS, make_handler(inbox, calls))
    assert request(app, "POST", "/telegram/webhook", headers=HEADERS, json=PAYLOAD).status_code == 200
    assert len(calls) == 2


def test_crashed_send_becomes_uncertain(inbox):
    _, owner = inbox.claim(123)
    inbox.transition(123, owner, "sending", lease_until=datetime.now(timezone.utc) - timedelta(seconds=1))
    reconstructed = FirestoreInbox(inbox.client, inbox.collection)
    assert reconstructed.claim(123)[0] == "uncertain"


def test_settings_repr_excludes_secrets():
    settings = Settings(telegram_bot_token="tokenprivate", telegram_webhook_secret="secretprivate", hash_salt="saltprivate", operator_token="operatorprivate")
    assert all(value not in repr(settings) for value in ["tokenprivate", "secretprivate", "saltprivate", "operatorprivate"])


def test_oversize_body_rejected_without_work():
    app = create_app(SETTINGS)
    response = request(app, "POST", "/telegram/webhook", headers=HEADERS, content=b" " * 256_001)
    assert response.status_code == 413


def test_transport_logging_redacts_bot_token(caplog):
    caplog.set_level("INFO", logger="httpx")
    api = TelegramAPI("secret-token", httpx.MockTransport(lambda _: httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})))
    assert api.send_message(9, "Test") == 1
    assert "secret-token" not in caplog.text
    assert "bot[redacted]" in caplog.text


def test_operator_token_uses_documented_alias(monkeypatch):
    monkeypatch.setenv("DEMO_OPERATOR_TOKEN", "test-operator-marker")
    monkeypatch.setenv("OPERATOR_TOKEN", "incorrect-legacy-name")
    settings = load_settings()
    assert settings.operator_token == "test-operator-marker"
    assert "test-operator-marker" not in repr(settings)


def test_unsupported_private_payload_is_not_persisted(inbox):
    payload = {
        "update_id": 123,
        "message": {
            "message_id": 8,
            "chat": {"id": 9, "type": "private", "first_name": "Private owner"},
            "text": "Private unsupported message",
            "from": {"id": 42, "first_name": "Private sender"},
            "contact": {"phone_number": "+60000000000", "first_name": "Private contact"},
        },
    }
    calls = []
    app = create_app(SETTINGS, make_handler(inbox, calls))
    assert request(app, "POST", "/telegram/webhook", headers=HEADERS, json=payload).status_code == 200
    state = inbox.client.collection(inbox.collection).document("123").get().to_dict()
    assert set(state) == {"status", "owner", "lease_until", "updated_at", "outcome"}
    assert state["status"] == "done"
    assert state["outcome"] == "unsupported"
    assert calls == []


def test_message_disables_auto_preview_preserving_explicit_route_and_button():
    wire = []
    def transport(request):
        wire.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
    api = TelegramAPI("synthetic-token", httpx.MockTransport(transport))
    route = "https://www.google.com/maps/dir/?api=1&destination=3.0,101.0"
    markup = {"inline_keyboard": [[{"text": "View route", "url": route}]]}
    assert api.send_message(9, "Listed destination: " + route, reply_markup=markup) == 1
    assert wire == [{"chat_id": 9, "text": "Listed destination: " + route,
                     "reply_markup": markup, "link_preview_options": {"is_disabled": True}}]


def test_recovery_presend_recheck_failure_is_retryable_before_any_send(inbox):
    from api.inventory_models import InventoryReply
    class Onboarding:
        async def process(self,*args):return InventoryReply(text='Synthetic reply',kind='prompt')
    class Recovery:
        calls=0
        async def recheck_reply(self,sender,reply):
            self.calls+=1
            if self.calls==1:raise RuntimeError('Synthetic transient persistence failure')
            return reply
    calls=[];handler=make_handler(inbox,calls);handler.onboarding=Onboarding();handler.recovery=Recovery()
    payload=json.loads(json.dumps(PAYLOAD));payload['message']['date']=int(datetime.now(timezone.utc).timestamp())
    app=create_app(SETTINGS,handler)
    assert request(app,'POST','/telegram/webhook',headers=HEADERS,json=payload).status_code==503
    assert calls==[]
    assert next(inbox.client.collection(inbox.collection).stream()).to_dict()['status']=='retryable'
    assert request(app,'POST','/telegram/webhook',headers=HEADERS,json=payload).status_code==200
    assert len(calls)==1


@pytest.mark.parametrize('send_failure',[False,True])
def test_recovery_callback_ack_and_ambiguous_send_not_replayed(inbox,send_failure):
    from api.inventory_models import InventoryReply
    from api.telegram_webhook import Update
    calls=[]
    class API:
        def answer_callback_query(self,*args):calls.append('ack')
        def send_message(self,*args,**kwargs):
            calls.append('send')
            if send_failure:raise RuntimeError('Synthetic unknown send outcome')
            return 100
    class Recovery:
        async def declare(self,*args):return InventoryReply(text='Synthetic recovery prompt',kind='prompt')
        async def recheck_reply(self,sender,reply):return reply
    handler=TelegramHandler(inbox,API(),recovery=Recovery())
    update=Update.model_validate(dict(update_id=888,callback_query={'id':'synthetic-recovery-callback','from':{'id':9},'data':'recovery:'+'a'*32,'message':{'message_id':8,'chat':{'id':9,'type':'private'}}}))
    async def run():
        assert await handler.handle(update)==('uncertain' if send_failure else 'done')
        assert await handler.handle(update)==('uncertain' if send_failure else 'done')
        assert calls==['ack','send']
        assert next(inbox.client.collection(inbox.collection).stream()).to_dict()['status']==('uncertain' if send_failure else 'done')
    asyncio.run(run())
