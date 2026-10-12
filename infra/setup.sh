#!/usr/bin/env bash
# Run locally with GCP_PROJECT explicitly set. Never uses the active project.
set -euo pipefail

[[ "${1:-}" == "--apply" && $# == 1 ]] || { echo 'Usage: GCP_PROJECT=your-project ./infra/setup.sh --apply' >&2; exit 2; }
: "${GCP_PROJECT:?Set GCP_PROJECT explicitly; the active gcloud project is not used}"
[[ "$GCP_PROJECT" =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]] || { echo 'Invalid project ID' >&2; exit 2; }
region="${GCP_REGION:-asia-southeast1}"
[[ "$region" == asia-southeast1 ]] || { echo 'Task 2 requires asia-southeast1' >&2; exit 2; }
for tool in gcloud bq python3; do command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }; done
root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bucket="highground-media-$GCP_PROJECT"
sa="highground-api@$GCP_PROJECT.iam.gserviceaccount.com"
work="$(mktemp -d)"
trap 'rm -r "$work"' EXIT

# Only a documented NOT_FOUND permits creation. Authentication/permission/network
# failures must stop, rather than masquerading as missing resources.
exists() {
  if "$@" >"$work/resource.json" 2>"$work/error"; then return 0; fi
  if python3 - "$work/error" <<'PY'
import pathlib, sys
s = pathlib.Path(sys.argv[1]).read_text()
sys.exit(0 if 'NOT_FOUND' in s or 'Not found:' in s or 'HTTPError 404: The specified bucket does not exist.' in s else 1)
PY
  then return 1; fi
  cat "$work/error" >&2
  exit 1
}
validate() {
  python3 "$root/validate_resource.py" "$1" "$work/resource.json" "$2"
}

gcloud projects describe "$GCP_PROJECT" --project="$GCP_PROJECT" --format='value(projectId)' > /dev/null
project_number="$(gcloud projects describe "$GCP_PROJECT" --project="$GCP_PROJECT" --format='value(projectNumber)')"
[[ "$project_number" =~ ^[0-9]+$ ]] || { echo 'Missing project number' >&2; exit 1; }
billing="$(gcloud billing projects describe "$GCP_PROJECT" --project="$GCP_PROJECT" --format='value(billingEnabled)')"
[[ "$billing" == True || "$billing" == true ]] || { echo 'Project billing is not enabled' >&2; exit 1; }

gcloud services enable run.googleapis.com firestore.googleapis.com storage.googleapis.com pubsub.googleapis.com bigquery.googleapis.com cloudscheduler.googleapis.com aiplatform.googleapis.com secretmanager.googleapis.com iam.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com --project="$GCP_PROJECT" --quiet

if exists gcloud firestore databases describe --database='(default)' --project="$GCP_PROJECT" --format=json; then
  validate firestore "$region"
else
  gcloud firestore databases create --database='(default)' --location="$region" --type=firestore-native --project="$GCP_PROJECT" --quiet
fi
if exists gcloud storage buckets describe "gs://$bucket" --project="$GCP_PROJECT" --raw --format=json; then
  validate bucket "$GCP_PROJECT/$project_number"
else
  gcloud storage buckets create "gs://$bucket" --location="$region" --uniform-bucket-level-access --public-access-prevention --project="$GCP_PROJECT" --quiet
fi
if ! exists gcloud pubsub topics describe flood-events --project="$GCP_PROJECT" --format=json; then
  gcloud pubsub topics create flood-events --project="$GCP_PROJECT" --quiet
fi
if exists bq --project_id="$GCP_PROJECT" show --format=prettyjson "$GCP_PROJECT:highground"; then
  validate dataset "$region"
else
  bq --project_id="$GCP_PROJECT" --location="$region" mk --dataset "$GCP_PROJECT:highground"
fi
for table in events alerts confirmations evidence_ledger outcomes; do
  if exists bq --project_id="$GCP_PROJECT" show --format=prettyjson "$GCP_PROJECT:highground.$table"; then
    validate table "$root/schemas/$table.json"
  else
    bq --project_id="$GCP_PROJECT" --location="$region" mk --table "$GCP_PROJECT:highground.$table" "$root/schemas/$table.json"
  fi
done
if exists gcloud iam service-accounts describe "$sa" --project="$GCP_PROJECT" --format=json; then
  validate service_account "$sa"
else
  gcloud iam service-accounts create highground-api --display-name='HighGround API runtime' --project="$GCP_PROJECT" --quiet
fi
for role in roles/datastore.user roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$GCP_PROJECT" --member="serviceAccount:$sa" --role="$role" --project="$GCP_PROJECT" --quiet > /dev/null
done
for role in roles/storage.objectCreator roles/storage.objectViewer; do
  gcloud storage buckets add-iam-policy-binding "gs://$bucket" --member="serviceAccount:$sa" --role="$role" --project="$GCP_PROJECT" --quiet > /dev/null
done
gcloud pubsub topics add-iam-policy-binding flood-events --member="serviceAccount:$sa" --role=roles/pubsub.publisher --project="$GCP_PROJECT" --quiet > /dev/null
for secret in TELEGRAM_BOT_TOKEN TELEGRAM_WEBHOOK_SECRET; do
  if exists gcloud secrets describe "$secret" --project="$GCP_PROJECT" --format=json; then
    validate secret "$region"
  else
    gcloud secrets create "$secret" --replication-policy=user-managed --locations="$region" --project="$GCP_PROJECT" --quiet
  fi
  gcloud secrets add-iam-policy-binding "$secret" --member="serviceAccount:$sa" --role=roles/secretmanager.secretAccessor --project="$GCP_PROJECT" --quiet > /dev/null
done
# Streaming insert permission, without table/dataset management or query jobs.
# updateData also permits destructive row writes: append-only is an application
# contract, not a guarantee that this IAM permission enforces immutability.
if exists gcloud iam roles describe highgroundEventWriter --project="$GCP_PROJECT" --format=json; then
  validate role 'bigquery.tables.get,bigquery.tables.updateData'
else
  gcloud iam roles create highgroundEventWriter --project="$GCP_PROJECT" --title='HighGround event append writer' --permissions=bigquery.tables.get,bigquery.tables.updateData --stage=GA --quiet
fi
for table in events alerts confirmations evidence_ledger outcomes; do
  bq --project_id="$GCP_PROJECT" add-iam-policy-binding --table=true --member="serviceAccount:$sa" --role="projects/$GCP_PROJECT/roles/highgroundEventWriter" "$GCP_PROJECT:highground.$table" > /dev/null
done
printf 'Setup commands completed for %s. Telegram secrets have no versions until populated separately.\n' "$GCP_PROJECT"
