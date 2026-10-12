"""Explicit local virtual delivery; never a Telegram identity or acceptance."""
import os
from api.config import Settings
from api.tools.emulators import loopback_endpoint


def require_local_demo(settings:Settings) -> None:
    if not settings.local_development or not settings.demo_mode:
        raise ValueError('Virtual demo transport requires local development and demo mode')
    for name,http in (('FIRESTORE_EMULATOR_HOST',False),('PUBSUB_EMULATOR_HOST',False),('BIGQUERY_EMULATOR_HOST',True)):
        loopback_endpoint(os.environ.get(name,''),http=http)


class LocalVirtualDelivery:
    def deliver(self, alert: dict) -> None:
        if alert.get('is_demo') is not True or alert.get('delivery_provenance')!='local_virtual' or not alert.get('virtual_recipient') or 'telegram_chat_id' in alert:
            raise ValueError('Virtual delivery is restricted to server-owned synthetic recipients')
        # The durable outbox records this simulation. No external transport occurs,
        # and no message ID, API acceptance, reading or self-report is invented.
