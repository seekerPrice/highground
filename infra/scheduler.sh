#!/usr/bin/env bash
# Prepared for manual hosted use only. No resource creation during local acceptance.
set -euo pipefail
if [[ "${HOSTING_AUTHORIZED:-false}" != "true" ]]; then
  echo "Hosting is deferred. Set HOSTING_AUTHORIZED=true only after explicit hosting authorization." >&2
  exit 1
fi
: "${GCP_PROJECT:?Explicit HighGround project required}"
: "${SCHEDULER_LOCATION:?Scheduler region required}"
: "${SCHEDULER_AUDIENCE:?Exact OIDC audience required}"
: "${SCHEDULER_CALLER_EMAIL:?Dedicated caller email required}"
: "${SCHEDULER_CALLER_SUBJECT:?Exact numeric caller subject required}"
: "${API_BASE_URL:?API HTTPS base URL required}"
python3 - <<'PY'
import os,re
from urllib.parse import urlsplit
project=os.environ['GCP_PROJECT']
if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]',project) or project=='dover-tts':raise ValueError('Explicit dedicated project required')
for name in ('API_BASE_URL','SCHEDULER_AUDIENCE'):
    url=urlsplit(os.environ[name])
    if url.scheme!='https' or not url.hostname or url.query or url.fragment or url.username or url.password:raise ValueError('Explicit HTTPS URL without query required')
if not os.environ['SCHEDULER_CALLER_EMAIL'].endswith('@'+project+'.iam.gserviceaccount.com'):raise ValueError('Caller must belong to target project')
if not os.environ['SCHEDULER_CALLER_SUBJECT'].isdigit():raise ValueError('Numeric IAM subject required')
PY
actual_subject="$(gcloud iam service-accounts describe "$SCHEDULER_CALLER_EMAIL" --project="$GCP_PROJECT" --format='value(uniqueId)')"
[[ "$actual_subject" == "$SCHEDULER_CALLER_SUBJECT" ]] || { echo "Configured caller subject does not match IAM." >&2; exit 1; }
job="highground-poll-warnings"
if gcloud scheduler jobs describe "$job" --project="$GCP_PROJECT" --location="$SCHEDULER_LOCATION" >/dev/null; then
  operation=update
else
  # A failed lookup must not be assumed to mean absence (permission/network errors).
  count="$(gcloud scheduler jobs list --project="$GCP_PROJECT" --location="$SCHEDULER_LOCATION" --filter="name:$job" --format='value(name)')"
  [[ -z "$count" ]] || exit 1
  operation=create
fi
gcloud scheduler jobs "$operation" http "$job" --project="$GCP_PROJECT" --location="$SCHEDULER_LOCATION" \
  --schedule='*/5 * * * *' --time-zone='Asia/Kuala_Lumpur' --http-method=POST \
  --uri="${API_BASE_URL%/}/jobs/poll-warnings" --oidc-service-account-email="$SCHEDULER_CALLER_EMAIL" \
  --oidc-token-audience="$SCHEDULER_AUDIENCE"
