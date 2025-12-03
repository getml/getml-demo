# GCS Storage Integration Setup for Snowflake

This guide describes how to configure Snowflake to access Parquet files stored in Google Cloud Storage (GCS) for the Jaffle Shop dataset.

## Overview

Snowflake cannot access GCS buckets directly—even publicly accessible ones—without a **storage integration**. This integration creates a GCS service account that must be granted IAM permissions on the target bucket.

**Default data location:** `gs://static.getml.com/datasets/jaffle_shop/`

## Prerequisites

- Snowflake account with `ACCOUNTADMIN` role access
- GCP project editor access (to grant IAM permissions on the bucket)
- Python environment with `uv` configured

## Step 1: Create Storage Integration

Use the provided helper function to create the storage integration:

```python
from settings import SnowflakeSettings
from snowflake_session import create_session
from data import setup_gcs_integration

settings = SnowflakeSettings.from_env()
with create_session(settings) as session:
    info = setup_gcs_integration(session)
    print(f"Service account: {info.service_account}")
```

This creates the integration and prints the service account that needs IAM permissions.

For custom bucket locations:

```python
from data import setup_gcs_integration

info = setup_gcs_integration(
    session,
    integration_name="MY_CUSTOM_INTEGRATION",
    allowed_location="gcs://my-bucket/path/",
)
```

You can also retrieve info about an existing integration:

```python
from data import describe_storage_integration

info = describe_storage_integration(session, "GETML_GCS_INTEGRATION")
print(f"Service account: {info.service_account}")
```

## Step 2: Grant IAM Permissions in GCP

The Snowflake service account from Step 1 needs read access to the GCS bucket.

### Using gcloud CLI (Recommended)

```bash
# Set your project
gcloud config set project getml-infra

# Store the service account from Step 1
SERVICE_ACCOUNT="<service-account-from-step-1>@gcpeuropewestX-X-XXXX.iam.gserviceaccount.com"

# Grant Storage Object Viewer role on the bucket
gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT}:objectViewer" gs://static.getml.com

# Verify the binding was applied
gsutil iam get gs://static.getml.com
```

For granular permissions (alternative to objectViewer role):

```bash
# Create a custom role with minimal permissions
gcloud iam roles create snowflake_gcs_reader \
    --project=getml-infra \
    --title="Snowflake GCS Reader" \
    --permissions=storage.buckets.get,storage.objects.get,storage.objects.list

# Grant the custom role
gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT}:projects/getml-infra/roles/snowflake_gcs_reader" \
    gs://static.getml.com
```

### Using Google Cloud Console

1. Sign in to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **Cloud Storage → Buckets**
3. Select the bucket `static.getml.com`
4. Go to **Permissions → Grant Access**
5. Add the Snowflake service account email as a principal
6. Assign role: **Storage Object Viewer**
7. Click **Save**

## Step 3: Validate the Integration

Validate that Snowflake can access the GCS bucket:

```python
from data import validate_storage_integration

result = validate_storage_integration(session, "GETML_GCS_INTEGRATION")
print(result)  # Should show success
```

## Step 4: Configure Environment Variable

For the integration tests to use this storage integration, set the environment variable:

```bash
export GCS_STORAGE_INTEGRATION=GETML_GCS_INTEGRATION
```

Add this to your shell profile (`.bashrc`, `.zshrc`) or CI/CD secrets for persistence.

## Running Integration Tests

With the environment variable set, integration tests will automatically use the GCS storage integration:

```bash
cd integration/snowflake
uv run pytest tests/integration/ -v
```

## Troubleshooting

### Error: "Processing aborted due to error 300010"

This typically means the Snowflake service account doesn't have IAM permissions on the GCS bucket. Verify:

```bash
# Check current IAM bindings on the bucket
gsutil iam get gs://static.getml.com

# Verify the service account is listed with objectViewer or equivalent role
```

### Error: "Stage does not exist or not authorized"

The stage hasn't been created yet. The `load_jaffle_shop_data_parquet()` function creates it automatically during data ingestion.

### Error: "Storage integration not found"

Verify the integration exists:

```python
from data import describe_storage_integration

try:
    info = describe_storage_integration(session, "GETML_GCS_INTEGRATION")
    print(f"Integration exists: {info.enabled}")
except Exception as e:
    print(f"Integration not found: {e}")
```

### Domain Restriction Policy (GCP Organizations)

If your GCP organization was created after May 3, 2024, Google enforces domain restrictions by default. Update the organization policy:

```bash
# Check current policy
gcloud org-policies describe iam.allowedPolicyMemberDomains \
    --project=getml-infra

# If restricted, add Snowflake's domain to allowed list
# See: https://docs.snowflake.com/en/user-guide/data-load-gcs-allow
```

## Alternative: Using S3 Public Bucket

If GCS setup isn't possible, you can use a public S3 bucket with Parquet files instead:

```bash
export S3_BUCKET_URL=s3://your-public-bucket/jaffle_shop/
```

S3 public buckets don't require a storage integration—Snowflake can access them directly.

## References

- [Snowflake: Configuring an integration for Google Cloud Storage](https://docs.snowflake.com/en/user-guide/data-load-gcs-config)
- [Snowflake: CREATE STORAGE INTEGRATION](https://docs.snowflake.com/en/sql-reference/sql/create-storage-integration)
- [GCP: IAM for Cloud Storage](https://cloud.google.com/storage/docs/access-control/iam)
