"""Bounded, schema-validated async Gemini calls through configured Vertex AI."""
import asyncio
from typing import TYPE_CHECKING, TypeVar

import google.auth
import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from api.config import Settings

T = TypeVar('T', bound=BaseModel)


class ModelResponseError(RuntimeError):
    """Safe error without model response, prompt or credential details."""


def create_vertex_client(settings: 'Settings') -> genai.Client:
    if not settings.gcp_project.strip() or not settings.vertex_location.strip():
        raise ValueError('GCP_PROJECT and VERTEX_LOCATION are required for Gemini')
    credentials, _ = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform'],
        quota_project_id=settings.gcp_project,
    )
    return genai.Client(
        vertexai=True, project=settings.gcp_project, location=settings.vertex_location,
        credentials=credentials,
        http_options=types.HttpOptions(timeout=50000, retry_options=types.HttpRetryOptions(attempts=1)),
    )


async def generate_structured(*, client: genai.Client, model: str, prompt: str,
                              schema: type[T], timeout_seconds: float = 50,
                              max_output_tokens: int = 1024) -> T:
    """At most two attempts, including schema, timeout and transient failures.

    The caller owns client lifetime. SDK retries are disabled per request so this
    bound is real. Non-transient authorization/configuration failures do not retry.
    Do not pass private media here until the media-ingestion contract is implemented.
    """
    if not model.strip():
        raise ValueError('A configured Gemini model ID is required')
    if not prompt.strip():
        raise ValueError('prompt must not be empty')
    if not 0 < timeout_seconds <= 60 or not 0 < max_output_tokens <= 8192:
        raise ValueError('timeout/token limits must be finite and bounded')
    config = types.GenerateContentConfig(
        response_mime_type='application/json', response_schema=schema,
        max_output_tokens=max_output_tokens,
        thinking_config=types.ThinkingConfig(thinking_level='LOW'),
        http_options=types.HttpOptions(timeout=int(timeout_seconds*1000),
                                       retry_options=types.HttpRetryOptions(attempts=1)),
    )
    for attempt in range(2):
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(model=model, contents=prompt, config=config),
                timeout=timeout_seconds,
            )
            # Validate again even when the SDK returns an already parsed model.
            if response.parsed is not None:
                parsed = response.parsed
                if isinstance(parsed, BaseModel):
                    parsed = parsed.model_dump()
                return schema.model_validate(parsed, strict=True)
            if not response.text:
                raise ValueError('missing structured response')
            return schema.model_validate_json(response.text, strict=True)
        except (ValidationError, ValueError, TimeoutError, httpx.TransportError):
            if attempt == 1:
                raise ModelResponseError('Gemini did not return a valid structured response within limits') from None
        except errors.APIError as error:
            transient = isinstance(error.code, int) and (error.code in (408, 429) or 500 <= error.code < 600)
            if not transient or attempt == 1:
                raise ModelResponseError('Gemini request failed') from None
    raise ModelResponseError('Gemini request failed')
