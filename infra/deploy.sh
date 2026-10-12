#!/usr/bin/env bash
# Local manual helper only. Build/push images separately; never provisions resources.
# Runtime files are JSON objects (valid YAML), containing only non-secret values.
set -euo pipefail
[[ $# -le 1 && "${1:---dry-run}" =~ ^--(dry-run|execute)$ ]] || { echo 'Usage: infra/deploy.sh [--dry-run|--execute]' >&2; exit 2; }
python3 - "${1:---dry-run}" <<'PY'
import json, os, re, subprocess, sys
from urllib.parse import urlsplit

def require(name):
    value = os.environ.get(name, '')
    if not value: raise ValueError('Required explicit configuration: '+name)
    return value

def match(name, pattern):
    value = require(name)
    if not re.fullmatch(pattern, value): raise ValueError('Invalid '+name)
    return value

def https(value):
    url = urlsplit(value)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/') or url.port not in (None, 443):
        raise ValueError('Explicit HTTPS bare service origin required')

try:
    execute = sys.argv[1] == '--execute'
    if execute and os.environ.get('HOSTING_AUTHORIZED') != 'true':
        raise ValueError('Hosting is deferred; explicit authorization and HOSTING_AUTHORIZED=true required')
    project = match('GCP_PROJECT', r'[a-z][a-z0-9-]{4,28}[a-z0-9]')
    if project == 'dover-tts': raise ValueError('Unrelated project forbidden')
    region = match('GCP_REGION', r'[a-z]+-[a-z]+[0-9]')
    services = [match(n, r'[a-z][a-z0-9-]{0,47}[a-z0-9]') for n in ('API_SERVICE', 'WEB_SERVICE')]
    if services[0] == services[1]: raise ValueError('Separate API/web services required')
    accounts = [match(n, r'[a-z][a-z0-9-]+@'+re.escape(project)+r'\.iam\.gserviceaccount\.com') for n in ('API_SERVICE_ACCOUNT', 'WEB_SERVICE_ACCOUNT')]
    images = [match(n, re.escape(region)+r'-docker\.pkg\.dev/'+re.escape(project)+r'/[a-z0-9_-]+/[a-z0-9_-]+@sha256:[a-f0-9]{64}') for n in ('API_IMAGE', 'WEB_IMAGE')]
    paths = [require(n) for n in ('API_ENV_FILE', 'WEB_ENV_FILE')]
    def config(path, allowed):
        with open(path, encoding='utf-8') as file: value = json.load(file)
        if not isinstance(value, dict) or not value or set(value)-allowed or any(not isinstance(v,str) or not v or '\n' in v for v in value.values()):
            raise ValueError('Runtime file has unsupported/missing/non-string values; secrets must use bindings')
        return value
    api = config(paths[0], {'GCP_PROJECT','GCP_REGION','VERTEX_LOCATION','GEMINI_FAST_MODEL','GEMINI_PRO_MODEL','GCS_BUCKET','PUBSUB_TOPIC','BQ_DATASET','WEB_BASE_URL','API_BASE_URL','DEMO_MODE','TELEGRAM_BOT_USERNAME','GEOCODING_USER_AGENT','GEOCODING_BASE_URL','VEHICLE_ACTION_TARGET_MINUTES','STOCK_ACTION_TARGET_MINUTES','DEFAULT_ALERT_RADIUS_M','DESTINATION_SEARCH_RADIUS_M','OFFICIAL_MAX_AGE_MINUTES','SCHEDULER_AUDIENCE','SCHEDULER_CALLER_EMAIL','SCHEDULER_CALLER_SUBJECT','LOCAL_DEVELOPMENT','SCHEDULER_LOCAL_AUTH'})
    for name in ('VERTEX_LOCATION','GEMINI_FAST_MODEL','GEMINI_PRO_MODEL','GCS_BUCKET','PUBSUB_TOPIC','BQ_DATASET','SCHEDULER_AUDIENCE','SCHEDULER_CALLER_EMAIL','SCHEDULER_CALLER_SUBJECT','DEMO_MODE'):
        if not api.get(name): raise ValueError('Missing API runtime field: '+name)
    if api.get('GCP_PROJECT') != project or api.get('GCP_REGION') != region: raise ValueError('Runtime target mismatch')
    if any(api.get(n,'false') != 'false' for n in ('LOCAL_DEVELOPMENT','SCHEDULER_LOCAL_AUTH')): raise ValueError('Hosted local bypass forbidden')
    for name in ('API_BASE_URL','WEB_BASE_URL','SCHEDULER_AUDIENCE'): https(api.get(name,''))
    if not re.fullmatch(r'[a-z][a-z0-9-]+@'+re.escape(project)+r'\.iam\.gserviceaccount\.com',api['SCHEDULER_CALLER_EMAIL']) or not api['SCHEDULER_CALLER_SUBJECT'].isdigit(): raise ValueError('Exact Scheduler caller identity required')
    web = config(paths[1], {'HIGHGROUND_API_ORIGIN'})
    https(web.get('HIGHGROUND_API_ORIGIN',''))
    if web['HIGHGROUND_API_ORIGIN'].rstrip('/') != api['API_BASE_URL'].rstrip('/'): raise ValueError('Web/API origin mismatch')
    bindings = []
    for name in ('TELEGRAM_BOT_TOKEN','TELEGRAM_WEBHOOK_SECRET','HASH_SALT','DEMO_OPERATOR_TOKEN'):
        reference = match(name+'_SECRET', r'[a-zA-Z0-9_-]+:[1-9][0-9]*')
        bindings.append(name+'='+reference)
    commands = []
    for index in range(2):
        command = ['gcloud','run','deploy',services[index],'--project='+project,'--region='+region,'--image='+images[index],'--service-account='+accounts[index],'--env-vars-file='+paths[index],'--port=8080','--allow-unauthenticated','--quiet']
        if index == 0: command.append('--set-secrets='+','.join(bindings))
        commands.append(command)
    if not execute:
        print('Validated dry run: no external commands executed. API then web deployment planned; webhook and Scheduler remain separate explicit steps.')
    else:
        for command in commands: subprocess.run(command, check=True, timeout=600)
        print('Deploy commands completed. Hosted acceptance, webhook and Scheduler verification still required.')
except (ValueError, OSError, subprocess.SubprocessError) as error:
    # Configuration contents, credentials and command output are not reflected here.
    print('Deployment stopped: '+(str(error) if isinstance(error,ValueError) else type(error).__name__), file=sys.stderr)
    sys.exit(1)
PY
