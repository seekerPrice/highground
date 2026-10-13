"""Pure setup-failure cleanup regressions; no emulator access."""
from unittest.mock import Mock
from google.api_core.exceptions import NotFound
import pytest
from api.tests.test_dispatch_emulators import _cleanup_scope,_create_sink_resources


def test_bigquery_setup_failure_removes_exact_topic_subscription_and_closes_clients():
    sinks=Mock();subscriber=Mock();failure=RuntimeError('setup failure')
    sinks.analytics.create_dataset.side_effect=failure
    with pytest.raises(RuntimeError) as caught:
        with _cleanup_scope() as cleanup:
            cleanup.extend([sinks.analytics.close,sinks.publisher.stop,subscriber.close])
            _create_sink_resources(sinks,subscriber,'owned','unique_dataset','projects/owned/topics/unique','projects/owned/subscriptions/unique',cleanup)
    assert caught.value is failure
    sinks.publisher.delete_topic.assert_called_once_with(request={'topic':'projects/owned/topics/unique'},timeout=10,retry=None)
    subscriber.delete_subscription.assert_called_once_with(request={'subscription':'projects/owned/subscriptions/unique'},timeout=10,retry=None)
    sinks.analytics.delete_dataset.assert_called_once()
    sinks.analytics.close.assert_called_once();sinks.publisher.stop.assert_called_once();subscriber.close.assert_called_once()


def test_cleanup_failure_attempts_every_operation_and_preserves_primary():
    first=Mock(side_effect=ValueError('private SDK body'));missing=Mock(side_effect=NotFound('missing'));close=Mock();primary=RuntimeError('primary')
    with pytest.raises(RuntimeError) as caught:
        with _cleanup_scope() as cleanup:
            cleanup.extend([close,missing,first]);raise primary
    assert caught.value is primary and 'ValueError' in primary.__notes__[0]
    assert 'private SDK body' not in primary.__notes__[0]
    close.assert_called_once();missing.assert_called_once();first.assert_called_once()
    with pytest.raises(RuntimeError,match='cleanup failed'):
        with _cleanup_scope() as cleanup:cleanup.append(first)


def test_async_cleanup_preserves_original_assertion_and_closes_after_failure():
    import asyncio
    from unittest.mock import AsyncMock
    from api.tests.test_dispatch_emulators import _async_cleanup_scope
    async def run():
        close=AsyncMock();failure=AsyncMock(side_effect=ValueError('private SDK detail'));primary=AssertionError('primary')
        with pytest.raises(AssertionError) as caught:
            async with _async_cleanup_scope() as cleanup:
                cleanup.extend([close,failure]);raise primary
        assert caught.value is primary and 'ValueError' in primary.__notes__[0]
        assert 'private SDK detail' not in primary.__notes__[0]
        close.assert_awaited_once()
    asyncio.run(run())
