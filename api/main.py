"""HighGround API liveness endpoint."""

from typing import Literal

from fastapi import FastAPI

app = FastAPI(title="HighGround API")


@app.get("/healthz")
def healthz() -> dict[str, Literal["ok"]]:
    """Report process liveness, without checking external services."""
    return {"status": "ok"}
