"""
GCS to Databricks Delta Lake ingestion module.

This module provides functions to load parquet files from GCS
and write them as Delta tables in Databricks.

Example:
    # Assuming running from root of repository
    from integration.databricks.data import ingestion

    # Load all jaffle_shop tables
    ingestion.load_from_gcs(
        bucket="https://static.getml.com/datasets/jaffle_shop/",
        destination_schema="jaffle_shop"
    )

    # Or load specific tables
    ingestion.load_from_gcs(
        bucket="https://static.getml.com/datasets/jaffle_shop/",
        destination_schema="jaffle_shop",
        tables=["raw_customers", "raw_orders"]
    )
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pandas as pd
import requests
from databricks.connect import DatabricksSession
from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_BUCKET: Final[str] = "https://static.getml.com/datasets/jaffle_shop"
DEFAULT_CATALOG: Final[str] = "workspace"
DEFAULT_SCHEMA: Final[str] = "jaffle_shop"
DEFAULT_PROFILE: Final[str] = "Code17"

JAFFLE_SHOP_TABLES: Final[tuple[str, ...]] = (
    "raw_customers",
    "raw_items",
    "raw_orders",
    "raw_products",
    "raw_stores",
    "raw_supplies",
    "raw_tweets",
)


@dataclass(frozen=True)
class TableConfig:
    """Configuration for a Delta table to be created."""

    source_url: str
    table_name: str
    catalog: str
    schema: str

    @property
    def full_table_name(self) -> str:
        """Return fully qualified table name."""
        return f"{self.catalog}.{self.schema}.{self.table_name}"


def _download_parquet(url: str) -> pd.DataFrame:
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


def _create_spark_session(profile: str | None = None) -> SparkSession:
    """
    Create a Databricks Spark session using serverless compute.

    Uses Databricks CLI authentication. If profile is not specified,
    uses DATABRICKS_CONFIG_PROFILE env var or defaults to 'DEFAULT'.

    Args:
        profile: Databricks CLI profile name (optional).

    Returns:
        SparkSession connected to Databricks serverless compute.

    Raises:
        RuntimeError: If connection fails.
    """
    logger.info("Creating Databricks Spark session (serverless)...")
    try:
        profile_name = profile or os.environ.get(
            "DATABRICKS_CONFIG_PROFILE", DEFAULT_PROFILE
        )

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
        raise RuntimeError(f"Failed to connect to Databricks: {e}") from e


def _write_to_delta(
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


def _ensure_schema_exists(spark: SparkSession, catalog: str, schema: str) -> None:
    """Ensure the target schema exists, create if necessary."""
    logger.info(f"Ensuring schema exists: {catalog}.{schema}")
    _ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")  # pyright: ignore[reportUnknownMemberType]


def load_from_gcs(
    bucket: str = DEFAULT_BUCKET,
    destination_schema: str = DEFAULT_SCHEMA,
    destination_catalog: str = DEFAULT_CATALOG,
    tables: Sequence[str] | None = None,
    spark: SparkSession | None = None,
    profile: str | None = None,
) -> list[str]:
    """
    Load parquet files from GCS bucket to Databricks Delta Lake.

    Downloads parquet files from the specified GCS bucket and writes them
    as Delta tables in Databricks.

    Args:
        bucket: GCS bucket URL (default: jaffle_shop dataset).
        destination_schema: Target schema name in Databricks.
        destination_catalog: Target catalog name in Databricks.
        tables: List of table names to load. If None, loads all jaffle_shop tables.
        spark: Optional existing SparkSession. If None, creates a new one.
        profile: Databricks CLI profile name (optional).

    Returns:
        List of successfully loaded table names.

    Example:
        >>> from integration.databricks.data import ingestion
        >>> loaded = ingestion.load_from_gcs(
        ...     bucket="https://static.getml.com/datasets/jaffle_shop/",
        ...     destination_schema="RAW"
        ... )
        >>> print(f"Loaded {len(loaded)} tables")
    """
    table_names = list(tables) if tables else list(JAFFLE_SHOP_TABLES)

    logger.info(f"Loading {len(table_names)} tables from {bucket}")
    logger.info(f"Destination: {destination_catalog}.{destination_schema}")

    if spark is None:
        spark = _create_spark_session(profile=profile)

    _ensure_schema_exists(spark, destination_catalog, destination_schema)

    # Build table configs
    table_configs = [
        TableConfig(
            source_url=f"{bucket.rstrip('/')}/{name}.parquet",
            table_name=name,
            catalog=destination_catalog,
            schema=destination_schema,
        )
        for name in table_names
    ]

    # Load each table
    loaded_tables: list[str] = []
    for config in table_configs:
        try:
            pdf = _download_parquet(config.source_url)
            _write_to_delta(spark, pdf, config)
            loaded_tables.append(config.table_name)
        except requests.RequestException as e:
            logger.error(f"Failed to download {config.source_url}: {e}")
        except Exception as e:
            logger.error(f"Failed to write {config.table_name}: {e}")

    logger.info(f"Successfully loaded {len(loaded_tables)}/{len(table_names)} tables")
    return loaded_tables


def list_tables(
    schema: str = DEFAULT_SCHEMA,
    catalog: str = DEFAULT_CATALOG,
    spark: SparkSession | None = None,
    profile: str | None = None,
) -> list[str]:
    """
    List all tables in the specified schema.

    Args:
        schema: Schema name.
        catalog: Catalog name.
        spark: Optional existing SparkSession.
        profile: Databricks CLI profile name (optional).

    Returns:
        List of table names.
    """
    if spark is None:
        spark = _create_spark_session(profile=profile)

    rows = spark.sql(f"SHOW TABLES IN {catalog}.{schema}").collect()  # pyright: ignore[reportUnknownMemberType]
    return [row.tableName for row in rows]  # pyright: ignore[reportAny]
