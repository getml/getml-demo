# Databricks Data Integration

This directory contains modules for ingesting data from GCS into Databricks Delta Lake and preparing population tables for getML feature engineering.


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

### Python API (Recommended)

Use the modules directly in notebooks or scripts:

```python
from integration.databricks.data import ingestion, preparation

# Load raw data from GCS to Databricks
loaded_tables = ingestion.load_from_gcs(
    bucket="https://static.getml.com/datasets/jaffle_shop/",
    destination_schema="jaffle_shop"
)
print(f"Loaded {len(loaded_tables)} tables")
```

### Load Specific Tables

```python
from integration.databricks.data import ingestion

# Load only the tables you need
ingestion.load_from_gcs(
    destination_schema="RAW",
    tables=["raw_customers", "raw_orders", "raw_items", "raw_products"]
)
```

## Troubleshooting

### Authentication Errors

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
- Wait a few minutes and retry (serverless cold start can take few seconds or minutes)
- Check your quota in the Databricks workspace


