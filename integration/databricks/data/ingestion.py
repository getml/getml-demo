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

from io import BytesIO
import logging
import os
from collections.abc import Sequence


from dataclasses import dataclass
from typing import Final

import requests
from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import VolumeType
from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


# Default configuration
DEFAULT_BUCKET: Final[str] = "https://static.getml.com/datasets/jaffle_shop"
DEFAULT_CATALOG: Final[str] = "workspace"
DEFAULT_SCHEMA: Final[str] = "jaffle_shop"
DEFAULT_PROFILE: Final[str] = "DEFAULT"
STAGING_VOLUME: Final[str] = "ingestion_staging"

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


def _stream_from_url_to_volume(
    workspace: WorkspaceClient, url: str, volume_path: str
) -> None:
    """Stream file from URL directly to Databricks Volume."""
    logger.info(f"Streaming from {url} to volume: {volume_path}")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        _ = workspace.files.upload(
            volume_path, BytesIO(response.raw.read()), overwrite=True
        )


def _ensure_volume_exists(
    workspace: WorkspaceClient, catalog: str, schema: str, volume_name: str
) -> None:
    """Ensure the staging volume exists."""
    full_name = f"{catalog}.{schema}.{volume_name}"
    logger.info(f"Ensuring volume exists: {full_name}")
    try:
        _ = workspace.volumes.read(full_name)
    except Exception:
        logger.info(f"Volume {full_name} not found, creating...")
        _ = workspace.volumes.create(
            catalog_name=catalog,
            schema_name=schema,
            name=volume_name,
            volume_type=VolumeType.MANAGED,
        )


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
            "Make sure you've authenticated with: databricks auth login --host "
            + "<workspace-url>  --profile <profile-name>"
        )
        logger.error(
            "If using a named profile, set DATABRICKS_CONFIG_PROFILE=<profile-name>"
        )
        raise RuntimeError(f"Failed to connect to Databricks: {e}") from e


def _write_to_delta(
    spark: SparkSession,
    source_path: str,
    config: TableConfig,
) -> None:
    """Write a parquet file from Volume to Delta Lake as a managed table."""
    logger.info(f"Writing to Delta table: {config.full_table_name} from {source_path}")

    sdf = spark.read.parquet(source_path)

    sdf.write.format("delta").mode("overwrite").option(
        "overwriteSchema", "true"
    ).saveAsTable(config.full_table_name)

    logger.info(f"Successfully wrote to {config.full_table_name}")


def _ensure_schema_exists(spark: SparkSession, catalog: str, schema: str) -> None:
    """Ensure the target schema exists, create if necessary."""
    logger.info(f"Ensuring schema exists: {catalog}.{schema}")
    _ = spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")  # pyright: ignore[reportUnknownMemberType]


def _build_table_configs(
    bucket: str,
    table_names: Sequence[str],
    catalog: str,
    schema: str,
) -> list[TableConfig]:
    """Build TableConfig objects for all tables to be loaded."""
    return [
        TableConfig(
            source_url=f"{bucket.rstrip('/')}/{name}.parquet",
            table_name=name,
            catalog=catalog,
            schema=schema,
        )
        for name in table_names
    ]


def _cleanup_volume_file(workspace: WorkspaceClient, volume_path: str) -> None:
    """Clean up temporary file from volume, suppressing errors."""
    try:
        workspace.files.delete(volume_path)
    except Exception as e:
        logger.warning(f"Failed to clean up volume file {volume_path}: {e}")


def _process_single_table(
    workspace: WorkspaceClient,
    spark: SparkSession,
    config: TableConfig,
    volume_path: str,
) -> bool:
    """Process a single table: download, write to Delta, and cleanup.

    Returns:
        True if successful, False otherwise.
    """
    try:
        _stream_from_url_to_volume(workspace, config.source_url, volume_path)
        _write_to_delta(spark, volume_path, config)
        return True

    except requests.RequestException as e:
        logger.error(f"Failed to download {config.source_url}: {e}")
        return False

    except Exception as e:
        logger.error(f"Failed to process {config.table_name}: {e}")
        return False

    finally:
        _cleanup_volume_file(workspace, volume_path)


def load_from_gcs(
    bucket: str = DEFAULT_BUCKET,
    destination_schema: str = DEFAULT_SCHEMA,
    destination_catalog: str = DEFAULT_CATALOG,
    tables: Sequence[str] | None = None,
    spark: SparkSession | None = None,
    profile: str = DEFAULT_PROFILE,
    workspace: WorkspaceClient | None = None,
) -> list[str]:
    """
    Load parquet files from GCS bucket to Databricks Delta Lake.

    Streams parquet files from the specified GCS bucket to Databricks volume and then
    writes them from the volume to Delta Lake as managed tables in Databricks.

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

    if workspace is None:
        workspace = WorkspaceClient()

    _ensure_volume_exists(
        workspace, destination_catalog, destination_schema, STAGING_VOLUME
    )

    table_configs = _build_table_configs(
        bucket, table_names, destination_catalog, destination_schema
    )

    loaded_tables: list[str] = []
    for config in table_configs:
        volume_path = f"/Volumes/{destination_catalog}/{destination_schema}/{STAGING_VOLUME}/{config.table_name}.parquet"

        if _process_single_table(workspace, spark, config, volume_path):
            loaded_tables.append(config.table_name)

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
