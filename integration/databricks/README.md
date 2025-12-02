# Databricks Delta Lake Ingestion

This directory contains scripts to ingest data from GCS into Databricks Delta Lake for use with getML's Databricks Feature Store integration notebook.

## Prerequisites

- **Python 3.12** 
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

### 2. Create Python Virtual Environment

```bash
# Navigate to this directory
cd integration/databricks

# Create virtual environment with Python 3.12
python3.12 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Authenticate with Databricks

```bash
# Get your workspace URL from your Databricks Free Edition account
# It looks like: https://<workspace-id>.cloud.databricks.com

databricks auth login --host https://<your-workspace>.cloud.databricks.com
```

This will open a browser for OAuth authentication. After successful login, your credentials are cached locally.

### 4. Verify Authentication

```bash
databricks auth profiles
```

You should see your workspace listed.

## Usage

### Run the Ingestion Script

```bash
python ingest_to_databricks.py
```

This will:
1. Download 7 parquet files from the GCS bucket (jaffle_shop dataset):
   - `raw_customers.parquet`
   - `raw_items.parquet`
   - `raw_orders.parquet`
   - `raw_products.parquet`
   - `raw_stores.parquet`
   - `raw_supplies.parquet`
   - `raw_tweets.parquet`
2. Write each as a Delta table in `workspace.default`:
   - `workspace.default.raw_customers`
   - `workspace.default.raw_items`
   - `workspace.default.raw_orders`
   - `workspace.default.raw_products`
   - `workspace.default.raw_stores`
   - `workspace.default.raw_supplies`
   - `workspace.default.raw_tweets`

### Verify in Databricks

After running the script, you can verify the tables in your Databricks workspace:

1. Open your Databricks workspace
2. Go to **Catalog** in the left sidebar
3. Navigate to `workspace` > `default`
4. You should see the 7 tables listed

Or run in a Databricks notebook:
```sql
SHOW TABLES IN workspace.default;

SELECT * FROM workspace.default.raw_customers LIMIT 10;
```

## Data Source

The parquet files are publicly accessible at:
- `https://static.getml.com/datasets/jaffle_shop/raw_customers.parquet`
- `https://static.getml.com/datasets/jaffle_shop/raw_items.parquet`
- `https://static.getml.com/datasets/jaffle_shop/raw_orders.parquet`
- `https://static.getml.com/datasets/jaffle_shop/raw_products.parquet`
- `https://static.getml.com/datasets/jaffle_shop/raw_stores.parquet`
- `https://static.getml.com/datasets/jaffle_shop/raw_supplies.parquet`
- `https://static.getml.com/datasets/jaffle_shop/raw_tweets.parquet`
- `https://static.getml.com/datasets/jaffle_shop/raw_tweets.parquet`

## Troubleshooting

### Authentication Errors

If you see authentication errors:
```bash
# Re-authenticate
databricks auth login --host https://<your-workspace>.cloud.databricks.com

# Check your profile
databricks auth env
```

### Python Version Issues

Databricks serverless requires Python 3.12:
```bash
python --version  # Should show 3.12.x

# If not, install Python 3.12 and recreate venv
brew install python@3.12  # macOS
```

### Connection Timeout

Free Edition has limited compute resources. If you see timeouts:
- Wait a few minutes and retry (serverless cold start)
- Check your quota in the Databricks workspace

## Next Steps

After ingestion, you can use these tables in the Databricks Feature Store integration notebook.
