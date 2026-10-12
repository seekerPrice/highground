# Task 2 infrastructure research and local verification

Baseline: 142178f. Latest user instruction: build fully locally first; hosting/resource provisioning is deferred. Scope: local provisioning script and resource schemas, not live provisioning. The unrelated active gcloud project is never selected or inferred. No cloud mutation has been performed during implementation. A confirmed HighGround project, enabled billing and operator permissions remain external prerequisites.

## Interface and decisions

Run deliberately from the repository root:

```sh
GCP_PROJECT=your-confirmed-project ./infra/setup.sh --apply
```

The script requires an explicit valid project ID, gcloud, bq and Python 3. It keeps GCP_REGION at the fixed asia-southeast1 location. Every gcloud/bq invocation has an explicit project flag, and resource identifiers include the project wherever applicable. It checks project/billing before enabling APIs. No local CLI project setting is changed, credential file is created or secret payload is read/printed.

The script enables Run, Firestore, Storage, Pub/Sub, BigQuery, Scheduler, Vertex AI, Secret Manager and IAM, plus Cloud Build and Artifact Registry for later manually invoked source builds. Enabling build services creates no repository trigger. [Cloud Run source deployment prerequisites](https://docs.cloud.google.com/run/docs/deploying-source-code), [enable services](https://docs.cloud.google.com/sdk/gcloud/reference/services/enable).

It creates or validates Firestore `(default)` Native mode in asia-southeast1; a wrong type/location aborts because these are not interchangeable deployment choices. [Firestore database commands](https://docs.cloud.google.com/firestore/native/docs/manage-databases), [gcloud create reference](https://docs.cloud.google.com/sdk/gcloud/reference/firestore/databases/create).

The media bucket name is `highground-media-PROJECT`. Existing buckets must match project number, location, uniform bucket access and enforced public access prevention. `--raw` gives stable API field names for validation. Creation uses uniform access and public access prevention. [bucket describe](https://docs.cloud.google.com/sdk/gcloud/reference/storage/buckets/describe), [bucket creation](https://docs.cloud.google.com/sdk/gcloud/reference/storage/buckets/create), [public access prevention](https://docs.cloud.google.com/storage/docs/public-access-prevention).

Pub/Sub topic `flood-events`, BigQuery dataset `highground` and five tables (`events`, `alerts`, `confirmations`, `evidence_ledger`, `outcomes`) follow the source spec. Existing dataset location and exact table schema/type are checked before reuse. Schema mismatch stops rather than silently changing production data. Schemas are initial application contracts; later approved model changes need a deliberate schema migration. [bq CLI reference](https://docs.cloud.google.com/bigquery/docs/reference/bq-cli-reference), [BigQuery table access](https://docs.cloud.google.com/bigquery/docs/control-access-to-resources-iam).

## Runtime identity and permission boundaries

`highground-api@PROJECT.iam.gserviceaccount.com` is the API identity; an existing disabled identity is rejected. It receives project-level `roles/datastore.user` and `roles/aiplatform.user`, required for application persistence and Vertex calls. Firestore's predefined application role permits writes/deletes; application policy remains necessary to preserve evidence documents. [Firestore IAM](https://docs.cloud.google.com/firestore/native/docs/security/iam), [Vertex IAM](https://docs.cloud.google.com/vertex-ai/docs/general/access-control).

Bucket-scoped `roles/storage.objectCreator` plus `roles/storage.objectViewer` enables original-byte ingestion and integrity rereads without object overwrite/delete. This intentionally does not yet implement policy-document deletion: the approved retention exception needs a separate narrowly controlled deletion path when that feature is authorized by the local Must gate. [Storage IAM role permissions](https://docs.cloud.google.com/storage/docs/access-control/iam-roles).

The runtime receives topic-scoped `roles/pubsub.publisher`; it gets no subscriber/admin grant. [Pub/Sub IAM](https://docs.cloud.google.com/pubsub/docs/access-control).

Empty Telegram token/webhook secret containers use user-managed replication in asia-southeast1, with secret-scoped `roles/secretmanager.secretAccessor` for the runtime. Existing replication must match. No secret version is created; populate payloads separately through the approved secret-management path. Replica locations cannot be changed later. [create secrets](https://docs.cloud.google.com/secret-manager/docs/creating-and-accessing-secrets), [replication policies](https://docs.cloud.google.com/secret-manager/docs/choosing-replication).

Custom role `highgroundEventWriter` contains only `bigquery.tables.get` and `bigquery.tables.updateData`, bound separately to each of the five tables using `bq add-iam-policy-binding --table=true`. It grants no dataset/table creation/deletion or query-job permission. Existing custom role permissions must exactly match. `tabledata.insertAll` requires updateData on its target table; the API SDK may fetch schema with tables.get. [insertAll permissions](https://docs.cloud.google.com/bigquery/docs/reference/rest/v2/tabledata/insertAll), [table IAM bindings](https://docs.cloud.google.com/bigquery/docs/control-access-to-resources-iam).

**Ledger limitation:** updateData is not an insert-only IAM capability. The ingestion implementation must exclusively append, avoid DML/update/delete paths, preserve upload bytes and record idempotent identifiers. BigQuery permissions alone do not establish immutable evidence. The runtime has no query-job permission here. Additional read/query requirements for later dashboard tasks must receive their own scoped grant after the actual query design is known.

Operator permissions differ from runtime permissions: the person executing setup must already be able to inspect billing, enable services, create these resources/service accounts/custom roles and set the specified resource policies. The script does not grant deployment/operator permissions to the runtime and does not create keys. Later Cloud Run deploy and Scheduler OIDC invoker grants require the actual service resource and are outside this setup slice.

## Verification

```sh
bash -n infra/setup.sh
python3 -m unittest discover -s infra/tests -v
```

Tests substitute gcloud/bq executables and record commands; they cover absent explicit project, existing compatible resources, missing resources, wrong Firestore region, bucket project ownership and permission-error fail-closed behavior. They inspect project flags, private bucket creation, exact table binding scope and absence of secret versions/keys. All intercepted commands run with PYTHONOPTIMIZE=1; explicit validators still reject conflicts. No test uses real credentials or proves live provisioning. Local CLI help was also inspected for `--raw`, secret replication flags, Firestore flags and bq table IAM syntax.

Local results: shell syntax exit 0; six contract tests passed (exit 0). A deliberate validator bypass caused the ownership and region tests to fail (exit 1), then restoring the checks returned six passing tests. Setup script is executable.

Actual cloud resource existence, IAM behavior and a successful live rerun remain unverified until hosting is explicitly authorized and root executes setup in the confirmed project. Provisioning is resumable after partial failure; it does not claim atomic rollback. Only documented not-found responses permit creation; unexpected failures stop the script.
