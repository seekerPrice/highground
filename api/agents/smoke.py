"""Explicit real Vertex schema smoke; synthetic prompt only, no alerts or media.

Usage: .venv/bin/python -m api.agents.smoke
This invokes the configured fast and Pro models and may incur model usage costs.
"""
import asyncio
from typing import Literal

from pydantic import BaseModel, ConfigDict

from api.config import load_settings
from api.tools.gemini import create_vertex_client, generate_structured


class SmokeResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['ok']


async def run() -> None:
    settings = load_settings()
    client = create_vertex_client(settings)
    try:
        for label, model in [('fast', settings.gemini_fast_model), ('pro', settings.gemini_pro_model)]:
            result = await generate_structured(
                client=client, model=model, schema=SmokeResult,
                prompt='Return JSON with status exactly ok. This is a synthetic schema connectivity test.',
            )
            print(f'{label} schema status={result.status}')
    finally:
        await client.aio.aclose()
        client.close()


if __name__ == '__main__':
    asyncio.run(run())
