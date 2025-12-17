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
from typing import TYPE_CHECKING, Final, cast

from pyspark.sql import Row

from integration.databricks.data._sql_loader import load_sql
from integration.databricks.data.models import (
    SchemaLocation,
    TableLocation,
)

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


class DataPreparationError(Exception):
    """Raised when data preparation fails."""


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

    Raises:
        DataPreparationError: If source tables are missing or preparation fails.

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

    _analyze_and_display_stores(spark, source_location.qualified_name)
    per_store = _create_weekly_stores_table(
        spark, source_location.qualified_name, target_location.qualified_name
    )
    _create_target_view(
        spark,
        source_location.qualified_name,
        target_location.qualified_name,
        population_table_location.table_name,
    )

    _display_sample_data(
        spark,
        target_location.qualified_name,
        per_store,
        population_table_location.table_name,
    )
    _display_store_statistics(
        spark, target_location.qualified_name, population_table_location.table_name
    )
    _display_overall_statistics(
        spark, target_location.qualified_name, population_table_location.table_name
    )
    _perform_data_quality_check(
        spark, target_location.qualified_name, population_table_location.table_name
    )
    _display_recent_snapshots(
        spark,
        target_location.qualified_name,
        per_store,
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

    try:
        for table_name in required_tables:
            table_location = TableLocation(
                table_name=table_name,
                location=schema_location,
            )
            result: list[Row] = spark.sql(
                "SELECT COUNT(*) as count FROM IDENTIFIER(:table_qualified_name) LIMIT 1",
                args={"table_qualified_name": table_location.qualified_name},
            ).collect()
            if not result:
                msg = (
                    f"Table {table_location.qualified_name} does not exist or is not "
                    "accessible. Please run ingestion first."
                )
                raise DataPreparationError(msg)

    except Exception as e:
        if isinstance(e, DataPreparationError):
            raise

        msg = (
            f"Failed to validate {schema_location.qualified_name} schema. "
            f"Ensure data has been loaded. Error: {e}"
        )
        raise DataPreparationError(msg) from e

    logger.info(
        f"✓ '{schema_location.qualified_name}' schema validated. It contains "
        + f"required tables: {required_tables}."
    )


def _ensure_target_schema(spark: SparkSession, target_schema: str) -> None:
    """Create target schema if it doesn't exist."""
    logger.info(f"Creating '{target_schema}' schema if not exists...")
    sql: str = load_sql("common/create_schema.sql")
    _ = spark.sql(sql, args={"full_schema_name": target_schema}).collect()
    logger.info(f"✓ '{target_schema}' schema ready")


# =============================================================================
# Data Preparation Pipeline
# =============================================================================


def _analyze_and_display_stores(spark: SparkSession, source_schema: str) -> None:
    """Analyze and display store activity."""
    logger.info("\n1. Analyzing store data...")
    stores: list[Row] = spark.sql(
        load_sql(path="preparation/analyze_stores.sql"),
        args={
            "stores_table": f"{source_schema}.raw_stores",
            "orders_table": f"{source_schema}.raw_orders",
        },
    ).collect()

    logger.info(f"\n{'Store':<30} {'Opened':<20} {'Orders':<12} {'Total Sales':<15}")
    logger.info("-" * 80)
    for store in stores:
        store_name = cast(str, store[1])
        opened_at = str(store[2])
        total_orders = cast(int, store[5])
        total_sales = cast(float, store[6])
        logger.info(
            f"{store_name:<30} {opened_at:<20} {total_orders:<12,} ${total_sales:<14,.2f}"
        )


def _create_weekly_stores_table(
    spark: SparkSession,
    source_schema: str,
    target_schema: str,
) -> list[Row]:
    """Create weekly_stores table with store-week combinations.

    Creates one row per store per week using reference_date (Monday week start).

    Returns:
        List of store information rows.
    """
    logger.info("\n2. Creating weekly_stores table (store-week combinations)...")
    logger.info("   reference_date is Monday (week start) from date_trunc('week', ...)")

    _ = spark.sql(
        load_sql(path="preparation/drop_weekly_stores.sql"),
        args={"table_qualified_name": f"{target_schema}.weekly_stores"},
    ).collect()
    _ = spark.sql(
        load_sql(
            path="preparation/create_weekly_stores.sql",
        ),
        args={
            "weekly_stores_table": f"{target_schema}.weekly_stores",
            "stores_table": f"{source_schema}.raw_stores",
            "orders_table": f"{source_schema}.raw_orders",
        },
    ).collect()

    # Get summary in single query: totals + per-store breakdown
    summary: list[Row] = spark.sql(
        load_sql(
            path="preparation/weekly_stores_summary.sql",
        ),
        args={
            "weekly_stores_table": f"{target_schema}.weekly_stores",
        },
    ).collect()

    # First row contains totals (same for all rows due to CROSS JOIN)
    num_snapshots: int = int(summary[0][0])
    num_stores: int = int(summary[0][1])
    logger.info(
        f"   Created {num_snapshots:,} weekly snapshots across {num_stores} stores"
    )

    # Extract per-store data (columns 2-5: store_name, num_snapshots, first, last)
    per_store: list[Row] = summary

    logger.info(f"\n   {'Store':<30} {'Snapshots':<12} {'First':<20} {'Last':<20}")
    logger.info("   " + "-" * 80)
    for row in per_store:
        store_name = cast(str, row[2])
        snapshots = cast(int, row[3])
        first_date = str(row[4])
        last_date = str(row[5])
        logger.info(
            f"   {store_name:<30} {snapshots:<12,} {first_date:<20} {last_date:<20}"
        )

    return per_store


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
    sql = load_sql(
        path="preparation/calculate_target.sql",
        orders_table=f"{source_schema}.raw_orders",
        weekly_stores_table=f"{target_schema}.weekly_stores",
        population_table=f"{target_schema}.{table_name}",
    )

    _ = spark.sql(sql).collect()


# =============================================================================
# Display and Analysis Functions
# =============================================================================


def _display_sample_data(
    spark: SparkSession,
    target_schema: str,
    per_store: list[Row],
    table_name: str,
) -> None:
    """Show sample data for first few stores."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("\n4. Sample data - first 5 snapshots per store:")
    logger.debug("-" * 120)

    for store_info in per_store[:3]:
        store_name: str = str(store_info[2])
        logger.debug(f"\n{store_name}:")
        sample_query: str = load_sql(
            path="preparation/snapshots_by_store.sql",
            order_direction="ASC",  # ASC: oldest first, "DESC" newest first
        )
        samples: list[Row] = spark.sql(
            sample_query,
            args={
                "population_table": f"{target_schema}.{table_name}",
                "store_name": store_name,
                "limit": 5,
            },
        ).collect()

        logger.debug(f"{'ID':<8} {'Week Start':<20} {'Sales $':<15} {'Orders':<10}")
        logger.debug("-" * 60)
        for row in samples:
            snapshot_id = cast(int, row[0])
            ref_date = str(row[1])
            sales = cast(float, row[2])
            orders = cast(int, row[3])
            logger.debug(
                f"{snapshot_id:<8} {ref_date:<20} ${sales:<14,.2f} {orders:<10,}"
            )


def _display_store_statistics(
    spark: SparkSession,
    target_schema: str,
    table_name: str,
) -> None:
    """Display target statistics per store."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("\n5. Target statistics per store:")
    logger.debug("-" * 120)

    store_stats: list[Row] = spark.sql(
        load_sql(
            path="preparation/store_statistics.sql",
        ),
        args={"population_table": f"{target_schema}.{table_name}"},
    ).collect()

    header = f"{'Store':<30} {'Snapshots':<12} {'Avg Week $':<15} {'Min $':<15} {'Max $':<15} {'Std Dev $':<15}"
    logger.debug(header)
    logger.debug("-" * 120)
    for row in store_stats:
        store = cast(str, row[0])
        snapshots = cast(int, row[1])
        avg_sales = cast(float, row[2])
        min_sales = cast(float, row[3])
        max_sales = cast(float, row[4])
        std_sales = cast(float, row[5])
        logger.debug(
            f"{store:<30} {snapshots:<12,} ${avg_sales:<14,.2f} ${min_sales:<14,.2f} ${max_sales:<14,.2f} ${std_sales:<14,.2f}"
        )


def _display_overall_statistics(
    spark: SparkSession,
    target_schema: str,
    table_name: str,
) -> None:
    """Display overall dataset statistics."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    overall: Row = spark.sql(
        load_sql(
            path="preparation/overall_statistics.sql",
        ),
        args={"population_table": f"{target_schema}.{table_name}"},
    ).collect()[0]

    logger.debug(f"""
6. Overall statistics:
--------------------------------------------------------------------------------
   Total snapshots: {overall[0]:,}
   Number of stores: {overall[1]:,}
   Average weekly sales per store: ${overall[2]:,.2f}
   Total sales in dataset: ${overall[3]:,.2f}
   Total orders in dataset: {overall[4]:,}
""")


def _perform_data_quality_check(
    spark: SparkSession,
    target_schema: str,
    table_name: str,
) -> None:
    """Perform and display data quality checks."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    quality: Row = spark.sql(
        load_sql(
            path="preparation/data_quality_check.sql",
        ),
        args={"population_table": f"{target_schema}.{table_name}"},
    ).collect()[0]

    logger.debug(f"""
7. Data quality check:
--------------------------------------------------------------------------------
   Total snapshots: {quality[0]:,}
   Weeks with zero sales: {quality[1]:,}
   Weeks with zero orders: {quality[2]:,}
   Invalid records (sales but no orders): {quality[3]:,}
""")

    zero_sales_count: int = int(quality[1])
    if zero_sales_count > 0:
        logger.warning(
            f"\n   WARNING: {zero_sales_count} snapshots have zero sales. Investigating..."
        )
        zero_sales: list[Row] = spark.sql(
            load_sql(
                path="preparation/zero_sales_investigation.sql",
            ),
            args={"population_table": f"{target_schema}.{table_name}"},
        ).collect()
        for row in zero_sales:
            logger.warning(f"      {row[0]}: {row[1]} weeks with zero sales")


def _display_recent_snapshots(
    spark: SparkSession,
    target_schema: str,
    per_store: list[Row],
    table_name: str,
) -> None:
    """Show most recent snapshots for first few stores."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("\n8. Most recent snapshots (last 3 per store):")
    logger.debug("-" * 120)

    for store_info in per_store[:3]:
        store_name: str = str(store_info[2])
        logger.debug(f"\n{store_name}:")
        recent_query: str = load_sql(
            path="preparation/snapshots_by_store.sql",
            order_direction="DESC",  # DESC: newest first, "ASC" oldest first
        )
        recent: list[Row] = spark.sql(
            recent_query,
            args={
                "population_table": f"{target_schema}.{table_name}",
                "store_name": store_name,
                "limit": 3,
            },
        ).collect()

        logger.debug(f"{'ID':<8} {'Week Start':<20} {'Sales $':<15} {'Orders':<10}")
        logger.debug("-" * 60)
        for row in recent:
            snapshot_id = cast(int, row[0])
            ref_date = str(row[1])
            sales = cast(float, row[2])
            orders = cast(int, row[3])
            logger.debug(
                f"{snapshot_id:<8} {ref_date:<20} ${sales:<14,.2f} {orders:<10,}"
            )
