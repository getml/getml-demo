"""Data ingestion from cloud storage to Snowflake for the Jaffle Shop dataset.

This module loads Parquet data from S3 or GCS buckets into Snowflake using
native COPY INTO commands with external staging. Schema is automatically
inferred from Parquet files using INFER_SCHEMA.

Supports:
- GCS buckets (requires STORAGE_INTEGRATION, auto-created if permissions exist)
- Public S3 buckets (no credentials required)

Usage example:
    from settings import SnowflakeSettings
    from snowflake_session import create_session
    from data import load_from_gcs, load_from_s3
    from bootstrap import setup_gcs_storage_integration

    with create_session(SnowflakeSettings.from_env()) as session:
        # Load from GCS (requires storage integration)
        results = load_from_gcs(
            session,
            storage_integration="GETML_GCS_INTEGRATION",
            integration_factory=setup_gcs_storage_integration,
        )

        # Or load from public S3 bucket
        results = load_from_s3(
            session,
            bucket="s3://my-public-bucket/jaffle_shop",
        )
"""

from __future__ import annotations

# ruff: noqa: G004, S608
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from snowflake.snowpark import Row, Session

from sql_loader import load_sql

if TYPE_CHECKING:
    from bootstrap import StorageIntegrationInfo

logger: logging.Logger = logging.getLogger(__name__)

IntegrationFactory = Callable[[Session, str, str], "StorageIntegrationInfo"]

JAFFLE_SHOP_TABLE_NAMES: list[str] = [
    "raw_customers",
    "raw_orders",
    "raw_order_items",
    "raw_products",
    "raw_stores",
    "raw_supplies",
]

DEFAULT_GCS_BUCKET = "gcs://static.getml.com/datasets/jaffle_shop"
DEFAULT_STAGE_NAME = "JAFFLE_SHOP_STAGE"


class DataIngestionError(Exception):
    """Raised when data ingestion fails."""


# =============================================================================
# Public API
# =============================================================================


def get_table_names(schema: str = "RAW") -> dict[str, str]:
    """Get fully qualified table names for Jaffle Shop data.

    Returns a dictionary mapping short table names (without 'raw_' prefix)
    to their fully qualified Snowflake table names.

    Args:
        schema: Schema where tables are located.

    Returns:
        Dictionary with keys like 'customers', 'orders', etc. and values
        like 'RAW.raw_customers', 'RAW.raw_orders', etc.

    Usage example:
        tables = get_table_names("RAW")
        orders_table = tables["orders"]  # "RAW.raw_orders"
        session.table(orders_table).to_arrow()
    """
    return {
        name.removeprefix("raw_"): f"{schema}.{name}"
        for name in JAFFLE_SHOP_TABLE_NAMES
    }


def load_from_gcs(
    session: Session,
    storage_integration: str,
    bucket: str = DEFAULT_GCS_BUCKET,
    destination_schema: str = "RAW",
    *,
    integration_factory: IntegrationFactory | None = None,
) -> dict[str, int]:
    """Load Jaffle Shop data from GCS bucket into Snowflake.

    Creates the destination schema if needed, sets up a Parquet file format
    and external stage pointing to the GCS bucket, then loads all tables
    using COPY INTO with schema inference.

    If the storage integration doesn't exist and an integration_factory is
    provided, attempts to create it automatically (requires ACCOUNTADMIN role).
    If no factory is provided and integration is missing, raises an error.

    Args:
        session: Active Snowflake Snowpark session.
        storage_integration: Name of the Snowflake storage integration for GCS.
        bucket: GCS bucket URL (gcs:// or gs:// prefix).
        destination_schema: Target schema name for loaded tables.
        integration_factory: Optional callable to create storage integration.
            Use bootstrap.setup_gcs_storage_integration for automatic creation.

    Raises:
        DataIngestionError: If storage integration is missing and no factory
            provided, or if data loading fails.
    """
    _ensure_storage_integration(
        session, storage_integration, bucket, integration_factory
    )

    return _load_data(
        session=session,
        bucket_url=bucket,
        destination_schema=destination_schema,
        storage_integration=storage_integration,
    )


def load_from_s3(
    session: Session,
    bucket: str,
    destination_schema: str = "RAW",
) -> dict[str, int]:
    """Load Jaffle Shop data from public S3 bucket into Snowflake.

    Creates the destination schema if needed, sets up a Parquet file format
    and external stage pointing to the S3 bucket, then loads all tables
    using COPY INTO with schema inference.

    Args:
        session: Active Snowflake Snowpark session.
        bucket: S3 bucket URL (s3:// prefix). Must be publicly accessible.
        destination_schema: Target schema name for loaded tables.

    Raises:
        DataIngestionError: If data loading fails.
    """
    if not bucket.lower().startswith("s3://"):
        raise DataIngestionError(
            f"Invalid S3 bucket URL: {bucket}. Must start with s3://"
        )

    return _load_data(
        session=session,
        bucket_url=bucket,
        destination_schema=destination_schema,
        storage_integration=None,
    )


# =============================================================================
# Storage Integration Handling
# =============================================================================


def _ensure_storage_integration(
    session: Session,
    integration_name: str,
    bucket_url: str,
    integration_factory: IntegrationFactory | None,
) -> None:
    """Ensure storage integration exists, creating it if factory is provided.

    Checks if the integration exists. If not and a factory is provided,
    attempts to create it. If no factory is provided and integration is
    missing, raises an error with instructions.
    """
    if _storage_integration_exists(session, integration_name):
        logger.info(f"✓ Storage integration '{integration_name}' verified")
        return

    if integration_factory is None:
        raise DataIngestionError(
            f"Storage integration '{integration_name}' does not exist. "
            f"Either create it manually, or pass integration_factory="
            f"bootstrap.setup_gcs_storage_integration to auto-create it "
            f"(requires ACCOUNTADMIN role)."
        )

    logger.info(f"Storage integration '{integration_name}' not found. Creating...")

    try:
        _ = integration_factory(
            session,
            integration_name,
            bucket_url,
        )
        logger.info(f"✓ Storage integration '{integration_name}' created")
    except Exception as e:
        raise DataIngestionError(
            f"Storage integration '{integration_name}' could not be created "
            f"(requires ACCOUNTADMIN role). Error: {e}"
        ) from e


def _storage_integration_exists(session: Session, integration_name: str) -> bool:
    """Check if a storage integration exists."""
    try:
        sql: str = load_sql(
            path="ingestion/describe_storage_integration.sql",
            integration_name=integration_name,
        )
        _ = session.sql(sql).collect()
    except Exception:  # noqa: BLE001
        return False
    else:
        return True


# =============================================================================
# Core Loading Logic
# =============================================================================


def _load_data(
    session: Session,
    bucket_url: str,
    destination_schema: str,
    storage_integration: str | None,
) -> dict[str, int]:
    """Core data loading logic shared by GCS and S3 loaders."""
    try:
        _ = session.sql("BEGIN").collect()
        _create_schema(session, destination_schema)
        _create_parquet_file_format(session, destination_schema)
        _create_external_stage(
            session,
            bucket_url=bucket_url,
            schema_name=destination_schema,
            storage_integration=storage_integration,
        )
        results = _load_all_tables(session, destination_schema)
        _ = session.sql("COMMIT").collect()
    except Exception as e:
        _rollback_transaction(session)
        raise DataIngestionError(
            f"Failed to load Jaffle Shop data into Snowflake. Error: {e}"
        ) from e

    _log_completion_summary(results, destination_schema)
    return results


def _create_schema(session: Session, schema_name: str) -> None:
    """Create schema if it doesn't exist."""
    logger.info(f"Creating {schema_name} schema if not exists...")
    sql: str = load_sql(path="ingestion/create_schema.sql", schema_name=schema_name)
    _ = session.sql(query=sql).collect()
    logger.info(f"✓ {schema_name} schema ready")


def _create_parquet_file_format(session: Session, schema_name: str) -> None:
    """Create Parquet file format for data ingestion."""
    logger.info("Creating Parquet file format...")
    sql: str = load_sql(
        path="ingestion/create_parquet_file_format.sql",
        schema_name=schema_name,
    )
    _ = session.sql(query=sql).collect()
    logger.info("✓ Parquet file format ready")


def _create_external_stage(
    session: Session,
    bucket_url: str,
    schema_name: str,
    storage_integration: str | None,
) -> None:
    """Create external stage pointing to cloud storage bucket."""
    logger.info(f"Creating external stage {DEFAULT_STAGE_NAME}...")

    if storage_integration:
        sql: str = load_sql(
            path="ingestion/create_stage_gcs.sql",
            stage_name=DEFAULT_STAGE_NAME,
            bucket_url=bucket_url,
            storage_integration=storage_integration,
            schema_name=schema_name,
        )
    else:
        sql = load_sql(
            path="ingestion/create_stage_s3_public.sql",
            stage_name=DEFAULT_STAGE_NAME,
            bucket_url=bucket_url,
            schema_name=schema_name,
        )

    _ = session.sql(query=sql).collect()
    logger.info(f"✓ External stage {DEFAULT_STAGE_NAME} created")


def _load_all_tables(session: Session, schema_name: str) -> dict[str, int]:
    """Load all Jaffle Shop tables from cloud storage."""
    logger.info("Loading tables from cloud storage...")
    results: dict[str, int] = {}

    for table_name in JAFFLE_SHOP_TABLE_NAMES:
        row_count: int = _load_single_table(session, table_name, schema_name)
        results[table_name] = row_count

    return results


def _load_single_table(
    session: Session,
    table_name: str,
    schema_name: str,
) -> int:
    """Load a single table from cloud storage using schema inference.

    Creates the table structure by inferring schema from the Parquet file,
    then copies data using column name matching.
    """
    logger.info(f"Loading {table_name}...")

    _ = session.sql(
        query=load_sql(
            path="ingestion/infer_and_create_table.sql",
            table_name=table_name,
            stage_name=DEFAULT_STAGE_NAME,
            schema_name=schema_name,
        )
    ).collect()

    copy_result: list[Row] = session.sql(
        query=load_sql(
            path="ingestion/copy_parquet.sql",
            table_name=table_name,
            stage_name=DEFAULT_STAGE_NAME,
            schema_name=schema_name,
        )
    ).collect()

    count_result: list[Row] = session.sql(
        query=f"SELECT COUNT(*) as count FROM {schema_name}.{table_name}"
    ).collect()

    row_count = int(count_result[0]["COUNT"])  # pyright: ignore[reportArgumentType]
    rows_copied = int(copy_result[0]["rows_loaded"]) if copy_result else 0  # pyright: ignore[reportArgumentType]

    logger.info(f"  ✓ {rows_copied:,} rows copied, {row_count:,} total rows in table")

    if row_count == 0:
        raise DataIngestionError(f"Table {table_name} has 0 rows after loading")

    return row_count


def _log_completion_summary(results: dict[str, int], schema_name: str) -> None:
    """Log summary of loaded tables."""
    table_lines = "\n".join(
        f"  • {name}: {count:,} rows" for name, count in results.items()
    )
    logger.info(f"""
================================================================================
DATA LOADING COMPLETE!
================================================================================
Successfully loaded {len(results)} tables into {schema_name} schema:
{table_lines}
""")


def _rollback_transaction(session: Session) -> None:
    """Attempt to rollback the current transaction."""
    try:
        _ = session.sql(query="ROLLBACK").collect()
        logger.warning("Transaction rolled back due to error")
    except Exception:  # noqa: BLE001
        logger.debug("Rollback failed - transaction may not have been active")
