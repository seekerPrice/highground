import asyncio
from types import SimpleNamespace

import pytest
from google.genai.errors import APIError
from pydantic import BaseModel, ConfigDict

from api.tools.gemini import ModelResponseError, generate_structured


class Result(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.aio = SimpleNamespace(models=self)

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        if value == 'timeout':
            await asyncio.sleep(1)
        return SimpleNamespace(parsed=None, text=value)


def run(client, **kwargs):
    return asyncio.run(generate_structured(client=client, model='configured-test-model',
                                          prompt='synthetic test', schema=Result, **kwargs))


def test_schema_and_sdk_retry_boundary():
    client = FakeClient(['{"unexpected":true}', '{"status":"ok"}'])
    assert run(client).status == 'ok' and len(client.calls) == 2
    config = client.calls[0]['config']
    assert config.response_schema == Result
    assert config.max_output_tokens == 1024
    assert config.http_options.retry_options.attempts == 1
    assert config.http_options.timeout == 50000


@pytest.mark.parametrize('values', [
    ['{}', '{}'], ['not JSON', 'not JSON'], ['timeout', 'timeout'],
    [APIError(503, {'message': 'synthetic'}), APIError(503, {'message': 'synthetic'})],
])
def test_bounded_failure(values):
    client = FakeClient(values)
    with pytest.raises(ModelResponseError):
        run(client, timeout_seconds=.01)
    assert len(client.calls) == 2


def test_transient_retry_then_success_and_permanent_no_retry():
    client = FakeClient([APIError(429, {'message': 'synthetic'}), '{"status":"ok"}'])
    assert run(client).status == 'ok' and len(client.calls) == 2
    client = FakeClient([APIError(403, {'message': 'private detail must not escape'})])
    with pytest.raises(ModelResponseError) as error:
        run(client)
    assert len(client.calls) == 1
    assert 'private detail' not in str(error.value)


def test_timeout_cancels_first_attempt_and_retry_can_succeed():
    client = FakeClient(['timeout', '{"status":"ok"}'])
    assert run(client, timeout_seconds=.01).status == 'ok'
    assert len(client.calls) == 2


def test_sdk_parsed_values_still_validated():
    client = FakeClient([])
    async def generate(**kwargs):
        client.calls.append(kwargs)
        return SimpleNamespace(parsed={'status': 123}, text='ignored')
    client.aio.models = SimpleNamespace(generate_content=generate)
    with pytest.raises(ModelResponseError):
        run(client)
    assert len(client.calls) == 2


@pytest.mark.parametrize('kwargs', [{'timeout_seconds': 0}, {'timeout_seconds': float('nan')},
                                     {'max_output_tokens': 9000}])
def test_invalid_limits_never_call_model(kwargs):
    client = FakeClient([])
    with pytest.raises(ValueError):
        run(client, **kwargs)
    assert not client.calls


def test_unknown_api_error_code_fails_safely_without_retry():
    error = APIError(403, {'message': 'synthetic'})
    error.code = None
    client = FakeClient([error])
    with pytest.raises(ModelResponseError):
        run(client)
    assert len(client.calls) == 1
