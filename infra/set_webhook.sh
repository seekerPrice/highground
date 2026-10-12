#!/usr/bin/env bash
# URL is public. Tokens are loaded inside Python, never shell arguments.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
[[ $# == 1 ]] || { echo 'Usage: ./infra/set_webhook.sh https://explicit-tunnel/telegram/webhook' >&2; exit 2; }
.venv/bin/python - "$1" <<'PY'
import re
import sys
from urllib.parse import urlsplit

import httpx
from api.config import load_settings

url = sys.argv[1]
parsed = urlsplit(url)
if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path != '/telegram/webhook':
    raise SystemExit('Provide an explicit HTTPS /telegram/webhook URL without credentials/query/fragment')
settings = load_settings()
if not settings.telegram_bot_token or not re.fullmatch(r'[A-Za-z0-9_-]{1,256}', settings.telegram_webhook_secret):
    raise SystemExit('Configure TELEGRAM_BOT_TOKEN and a valid TELEGRAM_WEBHOOK_SECRET privately')
try:
    with httpx.Client(timeout=20) as client:
        base = f'https://api.telegram.org/bot{settings.telegram_bot_token}'
        response = client.post(base + '/setWebhook', json={
            'url': url, 'secret_token': settings.telegram_webhook_secret,
            'allowed_updates': ['message'], 'drop_pending_updates': False,
        })
        response.raise_for_status()
        if response.json().get('ok') is not True:
            raise ValueError('setWebhook rejected')
        response = client.get(base + '/getWebhookInfo')
        response.raise_for_status()
        info = response.json()
        if info.get('ok') is not True or info.get('result', {}).get('url') != url:
            raise ValueError('Webhook URL mismatch')
except Exception:
    raise SystemExit('Webhook setup/verification failed; private details suppressed') from None
print('Telegram accepted the webhook URL; real callback delivery still needs verification.')
PY
