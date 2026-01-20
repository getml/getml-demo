"""Prepare weekly sales forecasting data for getML - BY STORE.

This module creates:
- weekly_stores table: Store-week combinations with reference_date (Monday week start)
- Population dynamic table with target (next week's sales)

reference_date is the Monday (week start) derived from DATE_TRUNC('week', ordered_at).

When settings are provided, the module auto-bootstraps required infrastructure
(warehouse and database) if they don't exist.

SQL queries are externalized in the sql/ directory for better maintainability.

Usage example:
    from data import (
        SnowflakeSettings,
        create_session,
        create_weekly_sales_by_store_with_target,
    )

    settings = SnowflakeSettings.from_env()
    with create_session(settings) as session:
        # Auto-bootstraps warehouse + database when settings are provided
        population_table = create_weekly_sales_by_store_with_target(
            session,
            settings=settings,
            source_schema="RAW",
            target_schema="PREPARED",
        )
        arrow_table = session.table(population_table).to_arrow()
"""

# ruff: noqa: G004, G003, S608, TRY301, E501

import logging
from typing import cast

from snowflake.snowpark import Row, Session

from ._bootstrap import ensure_infrastructure
from ._settings import SnowflakeSettings
from ._sql_loader import load_sql

logger: logging.Logger = logging.getLogger(__name__)


class DataPreparationError(Exception):
    """Raised when data preparation fails."""


# =============================================================================
# Public API
# =============================================================================


DEFAULT_POPULATION_TABLE_NAME = "WEEKLY_SALES_BY_STORE_WITH_TARGET"


def create_weekly_sales_by_store_with_target(
    session: Session,
    settings: SnowflakeSettings | None = None,
    source_schema: str = "RAW",
    target_schema: str = "PREPARED",
    table_name: str = DEFAULT_POPULATION_TABLE_NAME,
) -> str:
    """Create weekly sales forecasting data for getML, grouped by store.

    Creates:
    - weekly_stores: Table with store-week combinations (reference_date = Monday)
    - Population dynamic table with target column (configurable name via table_name)
    - Target: Sum of order_total for the 7-day window starting at reference_date

    When settings are provided, auto-bootstraps the warehouse and database
    if they don't exist.

    Args:
        session: Active Snowflake Snowpark session.
        settings: Optional settings for auto-bootstrapping warehouse and database.
            When provided, ensures infrastructure exists before preparing data.
        source_schema: Schema containing stores and orders tables.
        target_schema: Schema where prepared tables/views will be created.
        table_name: Name of the population view to create.

    Returns:
        Fully qualified table name (e.g., "PREPARED.WEEKLY_SALES_BY_STORE_WITH_TARGET").

    Raises:
        DataPreparationError: If source tables are missing or preparation fails.
        BootstrapError: If auto-bootstrap fails due to insufficient privileges.
    """
    if settings is not None:
        ensure_infrastructure(session, settings)
        if settings.warehouse:
            session.use_warehouse(settings.warehouse)
        if settings.database:
            session.use_database(settings.database)

    _validate_source_tables(session, source_schema)
    _ensure_target_schema(session, target_schema)

    logger.info("""
================================================================================
PREPARING WEEKLY SALES FORECASTING DATA BY STORE FOR getML
================================================================================
""")

    warehouse = session.get_current_warehouse()
    if not warehouse:
        raise DataPreparationError("No warehouse set. Required for dynamic table creation.")

    _analyze_and_display_stores(session, source_schema)
    per_store = _create_weekly_stores_dynamic_table(session, source_schema, target_schema, warehouse)
    _create_target_dynamic_table(session, source_schema, target_schema, table_name, warehouse)

    _display_sample_data(session, target_schema, per_store, table_name)
    _display_store_statistics(session, target_schema, table_name)
    _display_overall_statistics(session, target_schema, table_name)
    _perform_data_quality_check(session, target_schema, table_name)
    _display_recent_snapshots(session, target_schema, per_store, table_name)

    qualified_table_name = f"{target_schema}.{table_name}"

    logger.info(f"""
================================================================================
DATA PREPARATION COMPLETE!
================================================================================

Objects created in {target_schema} schema:
  - weekly_stores (DYNAMIC TABLE)
  - {table_name} (DYNAMIC TABLE - USE THIS FOR getML)

Population table: {qualified_table_name}
""")

    return qualified_table_name


# =============================================================================
# Validation and Schema Setup
# =============================================================================


def _validate_source_tables(session: Session, source_schema: str) -> None:
    """Validate that source schema exists and contains required tables."""
    required_tables: list[str] = ["stores", "orders"]
    logger.info(f"Validating {source_schema} schema and required tables...")

    try:
        for table_name in required_tables:
            result: list[Row] = session.sql(
                f"SELECT COUNT(*) as count FROM {source_schema}.{table_name} LIMIT 1"
            ).collect()
            if not result:
                raise DataPreparationError(
                    f"Table {source_schema}.{table_name} does not exist or is not "
                    "accessible. Please run ingestion first."
                )
    except DataPreparationError:
        raise
    except Exception as e:
        raise DataPreparationError(
            f"Failed to validate {source_schema} schema. "
            f"Ensure data has been loaded. Error: {e}"
        ) from e

    logger.info(f"✓ {source_schema} schema validated")


def _ensure_target_schema(session: Session, target_schema: str) -> None:
    """Create target schema if it doesn't exist."""
    logger.info(f"Creating {target_schema} schema if not exists...")
    sql: str = load_sql("common/create_schema.sql", schema_name=target_schema)
    _ = session.sql(query=sql).collect()
    logger.info(f"✓ {target_schema} schema ready")


# =============================================================================
# Data Preparation Pipeline
# =============================================================================


def _analyze_and_display_stores(session: Session, source_schema: str) -> None:
    """Analyze and display store activity."""
    logger.info("\n1. Analyzing store data...")
    stores: list[Row] = session.sql(
        query=load_sql(
            path="preparation/analyze_stores.sql", source_schema=source_schema
        )
    ).collect()

    logger.info(f"\n{'Store':<30} {'Opened':<20} {'Orders':<12} {'Total Sales':<15}")
    logger.info("-" * 80)
    for store in stores:
        logger.info(
            f"{store[1]:<30} {store[2]!s:<20} {store[5]:<12,} ${store[6]:<14,.2f}"
        )


def _create_weekly_stores_dynamic_table(
    session: Session,
    source_schema: str,
    target_schema: str,
    warehouse: str,
) -> list[Row]:
    """Create weekly_stores dynamic table with store-week combinations.

    Creates one row per store per week using reference_date (Monday week start).

    Returns:
        List of store information rows.
    """
    logger.info("\n2. Creating weekly_stores dynamic table (store-week combinations)...")
    logger.info("   reference_date is Monday (week start) from DATE_TRUNC('week', ...)")

    _ = session.sql(
        query=load_sql(
            path="preparation/create_weekly_stores.sql",
            source_schema=source_schema,
            target_schema=target_schema,
            warehouse=warehouse,
        )
    ).collect()

    # Get summary in single query: totals + per-store breakdown
    summary: list[Row] = session.sql(
        query=load_sql(
            path="preparation/weekly_stores_summary.sql",
            target_schema=target_schema,
        )
    ).collect()

    # First row contains totals (same for all rows due to CROSS JOIN)
    num_snapshots: int = cast("int", summary[0][0])
    num_stores: int = cast("int", summary[0][1])
    logger.info(
        f"   Created {num_snapshots:,} weekly snapshots across {num_stores} stores"
    )

    # Extract per-store data (columns 2-5: store_name, num_snapshots, first, last)
    per_store: list[Row] = summary

    logger.info(f"\n   {'Store':<30} {'Snapshots':<12} {'First':<20} {'Last':<20}")
    logger.info("   " + "-" * 80)
    for row in per_store:
        logger.info(f"   {row[2]:<30} {row[3]:<12,} {row[4]!s:<20} {row[5]!s:<20}")

    return per_store


def _create_target_dynamic_table(
    session: Session,
    source_schema: str,
    target_schema: str,
    table_name: str,
    warehouse: str,
) -> None:
    """Create dynamic table with target - total sales for the following week per store."""
    logger.info("\n3. Creating target dynamic table: next week's total sales per store...")
    _ = session.sql(
        query=load_sql(
            path="preparation/calculate_target.sql",
            source_schema=source_schema,
            target_schema=target_schema,
            table_name=table_name,
            warehouse=warehouse,
        )
    ).collect()


# =============================================================================
# Display and Analysis Functions
# =============================================================================


def _display_sample_data(
    session: Session,
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
        store_name: str = cast("str", store_info[2])
        logger.debug(f"\n{store_name}:")
        sample_query: str = load_sql(
            path="preparation/snapshots_by_store.sql",
            target_schema=target_schema,
            store_name=store_name,
            table_name=table_name,
            order_direction="",
            limit="5",
        )
        samples: list[Row] = session.sql(sample_query).collect()

        logger.debug(f"{'ID':<8} {'Week Start':<20} {'Sales $':<15} {'Orders':<10}")
        logger.debug("-" * 60)
        for row in samples:
            logger.debug(f"{row[0]:<8} {row[1]!s:<20} ${row[2]:<14,.2f} {row[3]:<10,}")


def _display_store_statistics(
    session: Session,
    target_schema: str,
    table_name: str,
) -> None:
    """Display target statistics per store."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    logger.debug("\n5. Target statistics per store:")
    logger.debug("-" * 120)

    store_stats: list[Row] = session.sql(
        query=load_sql(
            path="preparation/store_statistics.sql",
            target_schema=target_schema,
            table_name=table_name,
        )
    ).collect()

    logger.debug(
        f"{'Store':<30} {'Snapshots':<12} {'Avg Week $':<15} "
        f"{'Min $':<15} {'Max $':<15} {'Std Dev $':<15}"
    )
    logger.debug("-" * 120)
    for row in store_stats:
        logger.debug(
            f"{row[0]:<30} {row[1]:<12,} ${row[2]:<14,.2f} "
            f"${row[3]:<14,.2f} ${row[4]:<14,.2f} ${row[5]:<14,.2f}"
        )


def _display_overall_statistics(
    session: Session,
    target_schema: str,
    table_name: str,
) -> None:
    """Display overall dataset statistics."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    overall: Row = session.sql(
        query=load_sql(
            path="preparation/overall_statistics.sql",
            target_schema=target_schema,
            table_name=table_name,
        )
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
    session: Session,
    target_schema: str,
    table_name: str,
) -> None:
    """Perform and display data quality checks."""
    if not logger.isEnabledFor(logging.DEBUG):
        return

    quality: Row = session.sql(
        query=load_sql(
            path="preparation/data_quality_check.sql",
            target_schema=target_schema,
            table_name=table_name,
        )
    ).collect()[0]

    logger.debug(f"""
7. Data quality check:
--------------------------------------------------------------------------------
   Total snapshots: {quality[0]:,}
   Weeks with zero sales: {quality[1]:,}
   Weeks with zero orders: {quality[2]:,}
   Invalid records (sales but no orders): {quality[3]:,}
""")

    zero_sales_count: int = cast("int", quality[1])
    if zero_sales_count > 0:
        logger.warning(
            f"\n   WARNING: {zero_sales_count} snapshots have zero sales. Investigating..."
        )
        zero_sales: list[Row] = session.sql(
            query=load_sql(
                path="preparation/zero_sales_investigation.sql",
                target_schema=target_schema,
                table_name=table_name,
            )
        ).collect()
        for row in zero_sales:
            logger.warning(f"      {row[0]}: {row[1]} weeks with zero sales")


def _display_recent_snapshots(
    session: Session,
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
        store_name: str = cast("str", store_info[2])
        logger.debug(f"\n{store_name}:")
        recent_query: str = load_sql(
            path="preparation/snapshots_by_store.sql",
            target_schema=target_schema,
            store_name=store_name,
            table_name=table_name,
            order_direction="DESC",
            limit="3",
        )
        recent: list[Row] = session.sql(recent_query).collect()

        logger.debug(f"{'ID':<8} {'Week Start':<20} {'Sales $':<15} {'Orders':<10}")
        logger.debug("-" * 60)
        for row in recent:
            logger.debug(f"{row[0]:<8} {row[1]!s:<20} ${row[2]:<14,.2f} {row[3]:<10,}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    logger.info("This module requires a Snowflake session to be passed.")
    logger.info("Example usage:")
    logger.info("""
    from data import (
        SnowflakeSettings,
        create_session,
        create_weekly_sales_by_store_with_target,
    )

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        population_table = create_weekly_sales_by_store_with_target(
            session,
            table_name="WEEKLY_SALES_BY_STORE_WITH_TARGET",
        )
        # Use population_table with session.table(population_table).to_arrow()
    """)
