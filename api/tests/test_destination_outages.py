"""A listing-only transport failure must not prevent canonical Danger output."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from google.api_core.exceptions import DeadlineExceeded,ServiceUnavailable
from api.alert_composer import AlertComposer,render_danger
from api.destinations import DestinationLookup
from api.inventory_models import InventoryReply
from api.reply_guard import ReplyGuard
from api.tests.test_dispatch import NOW,shop

@pytest.mark.parametrize('failure',[DeadlineExceeded,ServiceUnavailable])
@pytest.mark.parametrize('entrypoint',['composer','final_reply_guard'])
def test_registry_transport_outage_preserves_fixed_danger(failure,entrypoint):
    client=Mock();client.collection.return_value.limit.return_value.stream.side_effect=failure('private registry detail')
    lookup=DestinationLookup(client)
    target=shop();expected,markup=render_danger('en',True,None)
    if entrypoint=='composer':
        rendered,snapshot,actual_markup=asyncio.run(AlertComposer(destinations=lookup).compose(
            dict(level='danger',is_demo=True,event_id='danger',created_at=NOW),target,'en'))
        assert snapshot.destination is None and not snapshot.items and snapshot.vehicle_target_at is None
    else:
        row=dict(target.model_dump(),language='en')
        guard=ReplyGuard(SimpleNamespace(shop_for_sender=lambda sender:row,danger_active=lambda identity:True),destinations=lookup)
        prior=InventoryReply(text='old optional video prompt',kind='prompt',shop_id=target.shop_id)
        reply=asyncio.run(guard.recheck_reply(123,prior));rendered,actual_markup=reply.text,reply.reply_markup
        assert reply.kind=='danger'
    assert rendered==expected and actual_markup==markup is None
    assert 'No listed destination is available.' in rendered
    client.collection.return_value.limit.return_value.stream.assert_called_once_with(timeout=8,retry=None)

@pytest.mark.parametrize('arguments',[(float('nan'),101.,('pps',)),(3.,101.,('unknown',))])
def test_registry_outage_fallback_does_not_hide_invalid_caller(arguments):
    client=Mock()
    with pytest.raises(ValueError):DestinationLookup(client).nearest(*arguments)
    client.collection.assert_not_called()
