"""Data ingestion from S3 to Snowflake for the Jaffle Shop dataset.

This module loads CSV data from a public S3 bucket into Snowflake's RAW schema
using native COPY INTO commands with external staging.

Usage example:
    from settings import SnowflakeSettings
    from snowflake_session import create_session
    from data import load_jaffle_shop_data

    with create_session(SnowflakeSettings.from_env()) as session:
        results = load_jaffle_shop_data(session)
"""

# ruff: noqa: G004, S608

import logging

from snowflake.snowpark import Row, Session

from ._sql_loader import load_sql

logger: logging.Logger = logging.getLogger(__name__)

JAFFLE_SHOP_TABLES: dict[str, str] = {
    "raw_customers": "(id TEXT, name TEXT)",
    "raw_orders": (
        "(id TEXT, customer TEXT, ordered_at TIMESTAMP, store_id TEXT, "
        "subtotal INTEGER, tax_paid INTEGER, order_total INTEGER)"
    ),
    "raw_order_items": "(id TEXT, order_id TEXT, sku TEXT)",
    "raw_products": "(sku TEXT, name TEXT, type TEXT, price INTEGER, description TEXT)",
    "raw_stores": "(id TEXT, name TEXT, opened_at TIMESTAMP, tax_rate FLOAT)",
    "raw_supplies": "(id TEXT, name TEXT, cost INTEGER, perishable BOOLEAN, sku TEXT)",
}

S3_BUCKET_URL = "s3://dbt-tutorial-public/long_term_dataset"
STAGE_NAME = "JAFFLE_SHOP_S3_STAGE"


def load_jaffle_shop_data(session: Session) -> dict[str, int]:
    """Load Jaffle Shop data from S3 into Snowflake RAW schema.

    Creates the RAW schema if needed, sets up an external stage pointing to
    the public S3 bucket, and loads all tables using COPY INTO commands.
    All operations are wrapped in a transaction that rolls back on failure.

    Raises:
        DataIngestionError: If schema creation, stage setup, or data loading fails.
    """
    try:
        _ = session.sql("BEGIN").collect()
        _create_raw_schema(session)
        _create_external_stage(session)
        results = _load_all_tables(session)
        _ = session.sql("COMMIT").collect()
    except Exception as e:
        rollback_transaction(session)
        raise DataIngestionError(
            f"Failed to load Jaffle Shop data into Snowflake. Error: {e}"
        ) from e

    _log_completion_summary(results)
    return results


class DataIngestionError(Exception):
    """Raised when data ingestion fails."""


def _create_raw_schema(session: Session) -> None:
    """Create RAW schema if it doesn't exist."""
    logger.info("Creating RAW schema if not exists...")
    _ = session.sql(load_sql("ingestion/create_raw_schema.sql")).collect()
    logger.info("✓ RAW schema ready")


def _create_external_stage(session: Session) -> None:
    """Create external stage pointing to S3 bucket."""
    logger.info(f"Creating external stage {STAGE_NAME}...")
    sql = load_sql(
        "ingestion/create_external_stage.sql",
        stage_name=STAGE_NAME,
        bucket_url=S3_BUCKET_URL,
    )
    _ = session.sql(sql).collect()
    logger.info(f"✓ External stage {STAGE_NAME} created")


def _load_all_tables(session: Session) -> dict[str, int]:
    """Load all Jaffle Shop tables from S3."""
    logger.info("Loading tables from S3...")
    results: dict[str, int] = {}

    for table_name, schema_def in JAFFLE_SHOP_TABLES.items():
        row_count = load_single_table(session, table_name, schema_def)
        results[table_name] = row_count

    return results


def load_single_table(session: Session, table_name: str, schema_def: str) -> int:
    """Load a single table from S3 and return row count."""
    logger.info(f"Loading {table_name}...")

    _ = session.sql(f"""
        CREATE OR REPLACE TABLE RAW.{table_name} {schema_def}
    """).collect()

    copy_result: list[Row] = session.sql(f"""
        COPY INTO RAW.{table_name}
        FROM @RAW.{STAGE_NAME}/{table_name}.csv
        FORCE = FALSE
    """).collect()

    count_result: list[Row] = session.sql(f"""
        SELECT COUNT(*) as count FROM RAW.{table_name}
    """).collect()

    # TODO: Research proper typing for Snowpark Row objects
    row_count = int(count_result[0]["COUNT"])  # pyright: ignore[reportArgumentType]
    rows_copied = int(copy_result[0]["rows_parsed"]) if copy_result else 0  # pyright: ignore[reportArgumentType]

    logger.info(f"  ✓ {rows_copied:,} rows copied, {row_count:,} total rows in table")

    if row_count == 0:
        raise DataIngestionError(f"Table {table_name} has 0 rows after loading")

    return row_count


def _log_completion_summary(results: dict[str, int]) -> None:
    """Log summary of loaded tables."""
    logger.info("=" * 80)
    logger.info("DATA LOADING COMPLETE!")
    logger.info("=" * 80)
    logger.info(f"Successfully loaded {len(results)} tables into RAW schema:")
    for table_name, count in results.items():
        logger.info(f"  • {table_name}: {count:,} rows")


def rollback_transaction(session: Session) -> None:
    """Attempt to rollback the current transaction."""
    try:
        _ = session.sql("ROLLBACK").collect()
        logger.warning("Transaction rolled back due to error")
    except Exception:  # noqa: BLE001
        logger.debug("Rollback failed - transaction may not have been active")
