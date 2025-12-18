"""Prepare weekly sales forecasting data for getML - BY STORE.

This module creates:
- weekly_stores table: Store-week combinations with reference_date (Monday week start)
- Population view with target (next week's sales)

reference_date is the Monday (week start) derived from date_trunc('week', ordered_at).

SQL queries are externalized in the sql/ directory for better maintainability.

Example:
    from integration.databricks.data import preparation
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()

    # Creates weekly sales forecasting data
    population_table = preparation.create_weekly_sales_by_store_with_target(
        spark,
        source_schema="workspace.raw",
        target_schema="workspace.prepared",
    )

    # Use the population table
    df = spark.table(population_table)
"""


# pyright: reportAny=none
# pyright: reportUnknownMemberType=none

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Final

from integration.databricks.data.models import (
    SchemaLocation,
    TableLocation,
)

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)
_SQL_DIR = Path(__file__).parent / "sql"


# =============================================================================
# Public API
# =============================================================================

REQUIRED_SOURCE_TABLES: Final[list[str]] = ["raw_stores", "raw_orders"]
DEFAULT_POPULATION_TABLE_NAME: Final[str] = "weekly_sales_by_store_with_target"


def create_weekly_sales_by_store_with_target(
    spark: SparkSession,
    source_catalog: str = "workspace",
    source_schema: str = "raw",
    target_catalog: str = "workspace",
    target_schema: str = "prepared",
    table_name: str = DEFAULT_POPULATION_TABLE_NAME,
) -> str:
    """Create weekly sales forecasting data for getML, grouped by store.

    Creates:
    - weekly_stores: Table with store-week combinations (reference_date = Monday)
    - Population view with target column (configurable name via table_name)
    - Target: Sum of order_total for the 7-day window starting at reference_date

    Args:
        spark: Active Spark session.
        source_catalog: Source catalog name.
        source_schema: Source schema name.
        target_catalog: Target catalog name.
        target_schema: Target schema name.
        table_name: Name of the population view to create.

    Returns:
        Fully qualified table name (e.g., "workspace.prepared.weekly_sales_by_store_with_target").

    Example:
        >>> from integration.databricks.data import preparation
        >>> from databricks.connect import DatabricksSession
        >>>
        >>> spark = DatabricksSession.builder.serverless().getOrCreate()
        >>> population_table = preparation.create_weekly_sales_by_store_with_target(
        ...     spark,
        ...     source_catalog="workspace",
        ...     source_schema="raw",
        ...     target_catalog="workspace",
        ...     target_schema="prepared",
        ... )
        >>> df = spark.table(population_table)
    """
    source_location = SchemaLocation(catalog=source_catalog, schema=source_schema)
    target_location = SchemaLocation(catalog=target_catalog, schema=target_schema)
    population_table_location = TableLocation(
        table_name=table_name, location=target_location
    )

    _validate_source_tables(spark, source_location)
    _ensure_target_schema(spark, target_location.qualified_name)

    logger.info("""
================================================================================
PREPARING WEEKLY SALES FORECASTING DATA BY STORE FOR GETML
================================================================================
""")

    _create_weekly_stores_table(
        spark, source_location.qualified_name, target_location.qualified_name
    )
    _create_target_view(
        spark,
        source_location.qualified_name,
        target_location.qualified_name,
        population_table_location.table_name,
    )

    qualified_table_name = (
        f"{target_location.qualified_name}.{population_table_location.table_name}"
    )

    logger.info(f"""
================================================================================
DATA PREPARATION COMPLETE!
================================================================================

Objects created in '{target_location.qualified_name}' schema:
- weekly_stores (Table)
- {population_table_location.table_name} (View - Use this for getML)

Population table: {qualified_table_name}
""")

    return qualified_table_name


# =============================================================================
# Validation and Schema Setup
# =============================================================================


def _validate_source_tables(
    spark: SparkSession,
    schema_location: SchemaLocation,
    required_tables: list[str] = REQUIRED_SOURCE_TABLES,
) -> None:
    """Validate that source schema exists and contains required tables."""
    logger.info(
        f"Validating '{schema_location.qualified_name}' schema and required tables..."
    )

    for table_name in required_tables:
        table_location = TableLocation(
            table_name=table_name,
            location=schema_location,
        )
        _ = spark.sql(
            "SELECT 1 FROM IDENTIFIER(:table_qualified_name) LIMIT 1",
            args={"table_qualified_name": table_location.qualified_name},
        ).collect()

    logger.info(
        f"✓ '{schema_location.qualified_name}' schema validated. It contains "
        + f"required tables: {required_tables}."
    )


def _ensure_target_schema(spark: SparkSession, target_schema: str) -> None:
    """Create target schema if it doesn't exist."""
    logger.info(f"Creating '{target_schema}' schema if not exists...")

    sql: str = "CREATE SCHEMA IF NOT EXISTS IDENTIFIER(:full_schema_name)"
    _ = spark.sql(sql, args={"full_schema_name": target_schema}).collect()

    logger.info(f"✓ '{target_schema}' schema ready")


# =============================================================================
# Data Preparation Pipeline
# =============================================================================


def _create_weekly_stores_table(
    spark: SparkSession,
    source_schema: str,
    target_schema: str,
) -> None:
    """Create weekly_stores table with store-week combinations.

    Creates one row per store per week using reference_date (Monday week start).
    """
    logger.info("\n2. Creating weekly_stores table (store-week combinations)...")
    logger.info("   reference_date is Monday (week start) from date_trunc('week', ...)")

    _ = spark.sql(
        "DROP TABLE IF EXISTS IDENTIFIER(:table_qualified_name)",
        args={"table_qualified_name": f"{target_schema}.weekly_stores"},
    ).collect()
    _ = spark.sql(
        (_SQL_DIR / "preparation/create_weekly_stores.sql").read_text(),
        args={
            "weekly_stores_table": f"{target_schema}.weekly_stores",
            "stores_table": f"{source_schema}.raw_stores",
            "orders_table": f"{source_schema}.raw_orders",
        },
    ).collect()


def _create_target_view(
    spark: SparkSession,
    source_schema: str,
    target_schema: str,
    table_name: str,
) -> None:
    """Create view with target - total sales for the following week per store."""
    logger.info("\n3. Creating target view: next week's total sales per store...")

    # Use python string formatting instead of Spark SQL parameters because
    # CREATE VIEW does not support parameter markers for identifiers.
    sql = (
        (_SQL_DIR / "preparation/calculate_target.sql")
        .read_text()
        .format(
            orders_table=f"{source_schema}.raw_orders",
            weekly_stores_table=f"{target_schema}.weekly_stores",
            population_table=f"{target_schema}.{table_name}",
        )
    )

    _ = spark.sql(sql).collect()


# =============================================================================
