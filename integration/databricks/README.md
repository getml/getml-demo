# Databricks Data Integration

This directory contains modules for ingesting data from GCS into Databricks Delta Lake and preparing population tables for getML feature engineering.


## Prerequisites

- **Databricks Free Edition account** (or higher tier)
- **Databricks CLI** installed

## Setup

### 1. Install Databricks CLI

```bash
# macOS
brew install databricks/tap/databricks

# Linux & macOS & Windows
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

More: https://docs.databricks.com/gcp/en/dev-tools/cli/install

### 2. Install Dependencies with uv

> [!IMPORTANT]  
> The `databricks` dependency group uses `databricks-connect`, which **cannot be installed alongside `pyspark`**. These packages are mutually exclusive. If you need local Spark execution (e.g., for notebooks like `imdb.ipynb`), use `uv run --group spark --isolated` instead to run in a temporary isolated environment.

```bash
# From the repository root
cd getml-demo

# Install uv if not already installed
pipx install uv

# Run jupyter lab after install dependencies included in the databricks group
$ uv run --group databricks jupyter-lab
```

### 3. Authenticate with Databricks

```bash
# Get your workspace URL from your Databricks Free Edition account
# It looks like: https://<workspace-id>.cloud.databricks.com

databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile DEFAULT
```

This will open a browser for OAuth authentication. After successful login, `DEFAULT` profile is stored in ~/.databrickscfg.

### 4. Verify Authentication

```bash
databricks auth profiles
```

You should see your workspace listed.


### 5. Configure the Databricks profile (optional)

The above steps created `DEFAULT` profile for Databricks authentication. The ingestion 
module also defaults to `DEFAULT` profile. The authentication should work smoothly for 
a single profile.

If you have multiple profiles (e.g for different Databricks hosts), you can set  
`DATABRICKS_CONFIG_PROFILE` environment variable in  `.mise.local.toml` (gitignored) to 
pin a specific profile to be used for this project:

```toml
[env]
DATABRICKS_CONFIG_PROFILE = "Code17"
```

In this example, `Code17` profile will be used instead of `DEFAULT` one.


## Usage

### Complete Workflow (Ingestion + Preparation)

For a complete end-to-end workflow that loads raw data and prepares it for getML:

```bash
# From repository root
uv run --group databricks python -m integration.databricks.prepare_jaffle_shop_data_for_databricks
```

Or in Python:

```python
from databricks.connect import DatabricksSession
from integration.databricks.data import ingestion, preparation

# Create Spark session
spark = DatabricksSession.builder.serverless().getOrCreate()

# Step 1: Load raw data from GCS
loaded_tables = ingestion.load_from_gcs(
    spark=spark,
    bucket="https://static.getml.com/datasets/jaffle_shop/",
    destination_catalog="workspace",
    destination_schema="raw",
)

# Step 2: Prepare weekly sales forecasting data
population_table = preparation.create_weekly_sales_by_store_with_target(
    spark,
    source_catalog="workspace",
    source_schema="raw",
    target_catalog="workspace",
    target_schema="prepared",
)

print(f"Population table ready: {population_table}")
```

### Python API: Ingestion Only

Load raw data from GCS to Databricks:

```python
from integration.databricks.data import ingestion

# Load all jaffle_shop tables
loaded_tables = ingestion.load_from_gcs(
    bucket="https://static.getml.com/datasets/jaffle_shop/",
    destination_schema="raw"
)
print(f"Loaded {len(loaded_tables)} tables")

# Or load specific tables
ingestion.load_from_gcs(
    destination_schema="raw",
    tables=["raw_customers", "raw_orders", "raw_items", "raw_products"]
)
```

### Python API: Preparation Only

Create weekly sales forecasting population table from existing raw data:

```python
from databricks.connect import DatabricksSession
from integration.databricks.data import preparation

spark = DatabricksSession.builder.serverless().getOrCreate()

# Create population table with target variable
population_table = preparation.create_weekly_sales_by_store_with_target(
    spark,
    source_catalog="workspace",
    source_schema="raw",
    target_catalog="workspace",
    target_schema="prepared",
    table_name="weekly_sales_by_store_with_target",
)

# Use the prepared data
df = spark.table(population_table)
df.show()
```

This creates:
- `weekly_stores` table: Store-week combinations with reference dates (Monday week starts)
- Population view with `next_week_sales` target variable for forecasting

## Troubleshooting

### Authentication Errors

```bash
# Re-authenticate
databricks auth login --host https://<your-workspace>.cloud.databricks.com

# Check your profile
databricks auth env
```

### Connection Timeout

Free Edition has limited compute resources. If you see timeouts:
- Wait a few minutes and retry (serverless cold start can take few seconds or minutes)
- Check your quota in the Databricks workspace


