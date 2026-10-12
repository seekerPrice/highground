"""User-initiated public-shop address search; explicit confirmation required."""
from datetime import datetime, timedelta, timezone
import hashlib
import math
from typing import Any
from urllib.parse import urlsplit

from google.cloud import firestore
import httpx
from starlette.concurrency import run_in_threadpool

from api.onboarding_store import OnboardingStore


class Geocoder:
    def __init__(self, store: OnboardingStore, *, user_agent: str, base_url: str = "https://nominatim.openstreetmap.org", transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.store = store
        self.user_agent = user_agent
        self.base_url = base_url
        self.transport = transport

    async def search(self, address: str) -> dict[str, Any] | None:
        if not self.user_agent.strip() or not 3 <= len(address) <= 200:
            return None
        parsed = urlsplit(self.base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            return None
        digest = hashlib.sha256(address.strip().casefold().encode()).hexdigest()
        cached = self.store.collection("geocode_cache").document(digest)
        cache = (await run_in_threadpool(cached.get)).to_dict() or {}
        now = datetime.now(timezone.utc)
        if cache and cache["until"] > now:
            return cache["candidate"]
        gate = self.store.collection("geocode_gate").document("application")

        @firestore.transactional
        def reserve(transaction: firestore.Transaction) -> bool:
            state = gate.get(transaction=transaction).to_dict() or {}
            if state.get("next_at", now) > now:
                return False
            transaction.set(gate, {"next_at": now + timedelta(seconds=1.1)})
            return True
        if not await run_in_threadpool(reserve, self.store.client.transaction()):
            return None
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=5) as client:
                response = await client.get(self.base_url.rstrip("/") + "/search", params={"q": address, "format": "jsonv2", "limit": 2, "countrycodes": "my"}, headers={"User-Agent": self.user_agent})
            response.raise_for_status()
            rows = response.json()
            if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
                return None
            if type(rows[0]["lat"]) not in (str, int, float) or type(rows[0]["lon"]) not in (str, int, float):
                return None
            lat, lng = float(rows[0]["lat"]), float(rows[0]["lon"])
            label = rows[0]["display_name"]
            if not math.isfinite(lat) or not math.isfinite(lng) or not -90 <= lat <= 90 or not -180 <= lng <= 180 or not isinstance(label, str) or not 1 <= len(label) <= 500:
                return None
            candidate = {"lat": lat, "lng": lng, "address_text": label}
            await run_in_threadpool(cached.set, {"candidate": candidate, "until": now + timedelta(days=1)})
            return candidate
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return None
