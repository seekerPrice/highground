"""Public synthetic waste estimates; no original, capability or owner identifiers."""
import asyncio
from contextlib import asynccontextmanager
from fastapi import APIRouter,Response
from api.waste_models import WasteResponse
from api.waste_store import WasteStore


def create_waste_router(settings,store=None):
    active=store;owns=store is None
    @asynccontextmanager
    async def lifespan(app):
        yield
        if owns and active:active.client.close()
    router=APIRouter(lifespan=lifespan)
    def configuration():return settings() if callable(settings) else settings
    def service():
        nonlocal active
        if active is None:
            from api.tools.firestore import create_firestore_client
            config=configuration();active=WasteStore(create_firestore_client(config),config.hash_salt)
        return active
    @router.get('/api/waste',response_model=WasteResponse)
    async def waste(response:Response):
        response.headers.update({'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'})
        return await asyncio.to_thread(service().public,configuration().lorry_capacity_m3)
    return router
