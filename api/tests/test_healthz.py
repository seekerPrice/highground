import asyncio

from httpx import ASGITransport, AsyncClient, Response

from api.main import app


def test_healthz_public_contract() -> None:
    async def request_health() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.get("/healthz")

    response = asyncio.run(request_health())
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}
