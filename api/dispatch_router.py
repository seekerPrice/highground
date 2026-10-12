"""Operator-only synthetic event creation; no private recipient data in responses."""
import hmac
from contextlib import asynccontextmanager

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing import Literal
from api.models import Level

from api.dispatch import DispatchService, create_dispatch_service
from api.dispatch_models import EventRequest
from api.dispatch_store import RequestConflict


class SimulationRequest(BaseModel):
    """Public DTO deliberately excludes trusted internal dispatch controls."""
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    request_id: str = Field(min_length=1, max_length=128, pattern=r'^[A-Za-z0-9_.:-]+$')
    source: Literal['demo'] = 'demo'
    level: Level
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    radius_m: int = Field(default=1000, ge=1, le=10000)
    confidence: float = Field(default=1, ge=0, le=1)
    reason: str = Field(default='Simulated warning', min_length=1, max_length=512)


def create_dispatch_router(settings, service: DispatchService | None = None) -> APIRouter:
    active = service
    owns_active = service is None
    @asynccontextmanager
    async def lifespan(application):
        try:
            yield
        finally:
            if owns_active and active is not None:
                await active.close()
    router = APIRouter(lifespan=lifespan)

    @router.post('/demo/simulate-warning')
    async def simulate(request: Request) -> dict:
        nonlocal active
        configuration = settings() if callable(settings) else settings
        if not configuration.demo_mode:
            raise HTTPException(403, 'Demo mode is disabled')
        if not configuration.operator_token:
            raise HTTPException(503, 'Demo operator authentication is not configured')
        supplied = request.headers.get('Authorization', '')
        expected = 'Bearer '+configuration.operator_token
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            raise HTTPException(403, 'Invalid demo operator token')
        payload = bytearray()
        async for chunk in request.stream():
            payload.extend(chunk)
            if len(payload) > 16_000:
                raise HTTPException(413, 'Event request too large')
        try:
            public = SimulationRequest.model_validate_json(bytes(payload))
            facts = public.model_dump()
            if 'radius_m' not in public.model_fields_set:
                facts['radius_m'] = configuration.default_alert_radius_m
            event = EventRequest.model_validate(facts)
            if event.source != 'demo':
                raise ValueError('Demo endpoint accepts simulated events only')
        except (ValueError, ValidationError):
            raise HTTPException(400, 'Invalid simulated event') from None
        try:
            if active is None:
                active = create_dispatch_service(configuration)
            return await active.process(event)
        except RequestConflict:
            raise HTTPException(409, 'Request identity conflicts with existing event') from None
        except Exception:
            raise HTTPException(503, 'Dispatch unavailable; retry with the same request_id') from None
    return router
