#!/usr/bin/env python3
"""
Ingest parquet files from GCS to Databricks Delta Lake.

This script downloads parquet files from a public GCS bucket and writes them
as Delta tables in Databricks using databricks-connect with serverless compute.

Usage:
    1. Authenticate with Databricks CLI: databricks auth login --host <workspace-url>
    2. Run: python ingest_to_databricks.py

Environment variables (optional, if not using CLI auth):
    DATABRICKS_HOST: Your Databricks workspace URL
    DATABRICKS_TOKEN: Personal access token
"""

from __future__ import annotations

import io
import logging
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd
import requests
from databricks.connect import DatabricksSession
from pyspark.sql import DataFrame, SparkSession

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
BASE_URL: Final[str] = "https://static.getml.com/datasets/jaffle_shop"
PARQUET_FILES: Final[tuple[str, ...]] = (
    "raw_customers.parquet",
    # "raw_items.parquet",
    # "raw_orders.parquet",
    "raw_products.parquet",
    "raw_stores.parquet",
    "raw_supplies.parquet",
    # "raw_tweets.parquet",
)
DEFAULT_CATALOG: Final[str] | None = "workspace"
DEFAULT_SCHEMA: Final[str] | None = "jaffle_shop"
PROFILE: Final[str] = "Code17"


@dataclass(frozen=True)
class TableConfig:
    """Configuration for a Delta table to be created."""

    source_url: str
    table_name: str
    catalog: str = DEFAULT_CATALOG
    schema: str = DEFAULT_SCHEMA

    @property
    def full_table_name(self) -> str:
        """Return fully qualified table name."""
        return f"{self.catalog}.{self.schema}.{self.table_name}"


def download_parquet(url: str) -> pd.DataFrame:
    """
    Download a parquet file from URL and return as pandas DataFrame.

    Falls back to saving to temp file if direct bytes reading fails.
    """
    logger.info(f"Downloading: {url}")
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    try:
        return pd.read_parquet(io.BytesIO(response.content))  # pyright: ignore[reportUnknownMemberType]
    except Exception:
        logger.warning("Direct read failed, using temp file fallback")
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            _ = tmp.write(response.content)
            tmp_path = tmp.name
        try:
            return pd.read_parquet(tmp_path)  # pyright: ignore[reportUnknownMemberType]
        finally:
            Path(tmp_path).unlink(missing_ok=True)


def create_spark_session(profile: str | None = None) -> SparkSession:
    """
    Create a Databricks Spark session using serverless compute.

    Uses Databricks CLI authentication. If profile is not specified,
    uses DATABRICKS_CONFIG_PROFILE env var or defaults to 'DEFAULT'.
    """
    logger.info("Creating Databricks Spark session (serverless)...")
    try:
        profile_name = profile or os.environ.get("DATABRICKS_CONFIG_PROFILE")

        if profile_name:
            logger.info(f"Using Databricks profile: {profile_name}")
            os.environ["DATABRICKS_CONFIG_PROFILE"] = profile_name

        spark = DatabricksSession.builder.serverless().getOrCreate()

        logger.info("Successfully connected to Databricks serverless compute")
        return spark
    except Exception as e:
        logger.error(f"Failed to create Databricks session: {e}")
        logger.error(
            "Make sure you've authenticated with: databricks auth login --host <workspace-url>"
        )
        logger.error(
            "If using a named profile, set DATABRICKS_CONFIG_PROFILE=<profile-name>"
        )
        raise


def write_to_delta(
    spark: SparkSession,
    pdf: pd.DataFrame,
    config: TableConfig,
) -> None:
    """Write a pandas DataFrame to Delta Lake as a managed table."""
    logger.info(f"Writing to Delta table: {config.full_table_name}")

    sdf: DataFrame = spark.createDataFrame(pdf)  # pyright: ignore[reportUnknownMemberType]

    sdf.write.format("delta").mode("overwrite").option(
        "overwriteSchema", "true"
    ).saveAsTable(config.full_table_name)

    logger.info(f"Successfully wrote {len(pdf)} rows to {config.full_table_name}")


def discover_catalog_schema(spark: SparkSession) -> tuple[str, str]:
    """Discover the current catalog and schema, or create one if needed."""
    current_catalog: str = spark.sql("SELECT current_catalog()").collect()[0][0]  # pyright: ignore[reportUnknownMemberType, reportAny]
    logger.info(f"Current catalog: {current_catalog}")

    schemas = spark.sql(f"SHOW SCHEMAS IN {current_catalog}").collect()  # pyright: ignore[reportUnknownMemberType]
    schema_names: list[str] = [row.databaseName for row in schemas]  # pyright: ignore[reportAny]
    logger.info(f"Available schemas: {schema_names}")

    # Use 'default' if it exists, otherwise use first available or create one
    target_schema = "default"
    if target_schema not in schema_names:
        if "getml_demo" in schema_names:
            target_schema = "getml_demo"
        elif schema_names:
            target_schema = schema_names[0]
        else:
            target_schema = "getml_demo"
            logger.info(f"Creating schema: {current_catalog}.{target_schema}")
            _ = spark.sql(  # pyright: ignore[reportUnknownMemberType]
                f"CREATE SCHEMA IF NOT EXISTS {current_catalog}.{target_schema}"
            )

    logger.info(f"Using catalog.schema: {current_catalog}.{target_schema}")
    return current_catalog, target_schema


def verify_tables(spark: SparkSession, catalog: str, schema: str) -> None:
    """Verify that all tables were created successfully."""
    logger.info(f"Verifying tables in {catalog}.{schema}...")
    rows = spark.sql(f"SHOW TABLES IN {catalog}.{schema}").collect()  # pyright: ignore[reportUnknownMemberType]
    table_names: list[str] = [row.tableName for row in rows]  # pyright: ignore[reportAny]
    logger.info(f"Tables found: {table_names}")


def resolve_catalog_schema(spark: SparkSession) -> tuple[str, str] | tuple[None, None]:
    """Resolve catalog and schema from defaults or by discovery."""

    catalog: str | None = DEFAULT_CATALOG
    schema: str | None = DEFAULT_SCHEMA

    if catalog is not None and schema is not None:
        logger.info(f"Using configured catalog.schema: {catalog}.{schema}")
        return catalog, schema

    try:
        return discover_catalog_schema(spark)
    except Exception as e:
        logger.error(f"Failed to discover catalog/schema: {e}")
        return None, None


def main() -> int:
    """Main entry point for the ingestion script."""
    logger.info("Starting parquet ingestion to Databricks Delta Lake")

    try:
        spark = create_spark_session(profile=PROFILE)
    except Exception:
        return 1

    catalog, schema = resolve_catalog_schema(spark)
    if catalog is None or schema is None:
        return 1

    table_configs = [
        TableConfig(
            source_url=f"{BASE_URL}/{filename}",
            table_name=Path(filename).stem,  # e.g., "product" from "product.parquet"
            catalog=catalog,
            schema=schema,
        )
        for filename in PARQUET_FILES
    ]

    success_count = 0
    for table_config in table_configs:
        try:
            pdf = download_parquet(table_config.source_url)
            write_to_delta(spark, pdf, table_config)
            success_count += 1
        except requests.RequestException as e:
            logger.error(f"Failed to download {table_config.source_url}: {e}")
        except Exception as e:
            logger.error(f"Failed to write {table_config.table_name}: {e}")

    if success_count > 0:
        verify_tables(spark, catalog, schema)

    logger.info(f"Completed: {success_count}/{len(table_configs)} tables ingested")
    return 0 if success_count == len(table_configs) else 1


if __name__ == "__main__":
    sys.exit(main())
