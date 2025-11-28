"""Prepare weekly sales forecasting data for getML - BY STORE.

This script creates a population table with weekly snapshots (Sunday nights)
per store and calculates the target: total sales for the following week.

Only includes full weeks where the store was open for the entire week.

SQL queries are externalized in the sql/ directory for better maintainability.
"""

# ruff: noqa: G004, G003, S608, TRY301, E501

import logging
from typing import cast

from snowflake.snowpark import Row, Session

from ._sql_loader import load_sql

logger: logging.Logger = logging.getLogger(__name__)


def validate_raw_schema(session: Session) -> None:
    """Validate that RAW schema exists and contains required tables."""
    required_tables: list[str] = ["raw_stores", "raw_orders"]
    logger.info("Validating RAW schema and required tables...")

    try:
        for table_name in required_tables:
            result: list[Row] = session.sql(
                f"SELECT COUNT(*) as count FROM RAW.{table_name} LIMIT 1"
            ).collect()
            if not result:
                msg: str = (
                    f"Table RAW.{table_name} does not exist or is not accessible. "
                    "Please run ingestion.load_jaffle_shop_data() first."
                )
                raise ValueError(msg)
    except Exception as e:
        msg = f"Failed to validate RAW schema. Ensure data has been loaded. Error: {e}"
        raise ValueError(msg) from e

    logger.info("✓ RAW schema validated")


def _ensure_prepared_schema(session: Session) -> None:
    """Create PREPARED schema if it doesn't exist."""
    logger.info("Creating PREPARED schema if not exists...")
    _ = session.sql(load_sql("preparation/create_prepared_schema.sql")).collect()
    logger.info("✓ PREPARED schema ready")


def _analyze_and_display_stores(session: Session) -> None:
    """Analyze and display store activity."""
    logger.info("\n1. Analyzing store data...")
    stores: list[Row] = session.sql(
        load_sql("preparation/analyze_stores.sql")
    ).collect()

    logger.info(f"\n{'Store':<30} {'Opened':<20} {'Orders':<12} {'Total Sales':<15}")
    logger.info("-" * 80)
    for store in stores:
        logger.info(
            f"{store[1]:<30} {store[2]!s:<20} {store[5]:<12,} ${store[6]:<14,.2f}"
        )


def _create_weekly_population_table(session: Session) -> list[Row]:
    """Create population table with Sunday night snapshots per store.

    Returns:
        List of store information rows.
    """
    logger.info(
        "\n2. Creating weekly population table per store (Sunday night snapshots)..."
    )
    logger.info("   Only including FULL weeks (store open entire week)...")

    _ = session.sql(
        load_sql("preparation/drop_population_weekly_by_store.sql")
    ).collect()
    _ = session.sql(
        load_sql("preparation/create_population_weekly_by_store.sql")
    ).collect()

    num_snapshots: int = cast(
        "int", session.sql(load_sql("preparation/count_snapshots.sql")).collect()[0][0]
    )
    num_stores: int = cast(
        "int", session.sql(load_sql("preparation/count_stores.sql")).collect()[0][0]
    )
    logger.info(
        f"   Created {num_snapshots:,} weekly snapshots across {num_stores} stores"
    )

    # Show snapshots per store
    per_store: list[Row] = session.sql(
        load_sql("preparation/snapshots_per_store.sql")
    ).collect()

    logger.info(f"\n   {'Store':<30} {'Snapshots':<12} {'First':<20} {'Last':<20}")
    logger.info("   " + "-" * 80)
    for row in per_store:
        logger.info(f"   {row[0]:<30} {row[1]:<12,} {row[2]!s:<20} {row[3]!s:<20}")

    return per_store


def _add_target_column(session: Session) -> None:
    """Calculate target - total sales for the following week per store."""
    logger.info("\n3. Calculating target: next week's total sales per store...")
    _ = session.sql(load_sql("preparation/drop_population_with_target.sql")).collect()
    _ = session.sql(load_sql("preparation/create_population_with_target.sql")).collect()


def _display_sample_data(session: Session, per_store: list[Row]) -> None:
    """Show sample data for first few stores."""
    logger.info("\n4. Sample data - first 5 snapshots per store:")
    logger.info("-" * 120)

    for store_info in per_store[:3]:  # Show first 3 stores
        store_name: str = cast("str", store_info[0])
        logger.info(f"\n{store_name}:")
        sample_query = load_sql(
            "preparation/sample_data_by_store.sql", store_name=store_name
        )
        samples: list[Row] = session.sql(sample_query).collect()

        logger.info(
            f"{'ID':<8} {'Snapshot (Sunday)':<20} {'Predict Week':<20} "
            f"{'Sales $':<15} {'Orders':<10}"
        )
        logger.info("-" * 80)
        for row in samples:
            logger.info(
                f"{row[0]:<8} {row[1]!s:<20} {row[2]!s:<20} "
                f"${row[3]:<14,.2f} {row[4]:<10,}"
            )


def _display_store_statistics(session: Session) -> None:
    """Display target statistics per store."""
    logger.info("\n5. Target statistics per store:")
    logger.info("-" * 120)

    store_stats: list[Row] = session.sql(
        load_sql("preparation/store_statistics.sql")
    ).collect()

    logger.info(
        f"{'Store':<30} {'Snapshots':<12} {'Avg Week $':<15} "
        f"{'Min $':<15} {'Max $':<15} {'Std Dev $':<15}"
    )
    logger.info("-" * 120)
    for row in store_stats:
        logger.info(
            f"{row[0]:<30} {row[1]:<12,} ${row[2]:<14,.2f} "
            f"${row[3]:<14,.2f} ${row[4]:<14,.2f} ${row[5]:<14,.2f}"
        )


def _display_overall_statistics(session: Session) -> None:
    """Display overall dataset statistics."""
    logger.info("\n6. Overall statistics:")
    logger.info("-" * 80)

    overall: Row = session.sql(
        load_sql("preparation/overall_statistics.sql")
    ).collect()[0]

    logger.info(f"   Total snapshots: {overall[0]:,}")
    logger.info(f"   Number of stores: {overall[1]:,}")
    logger.info(f"   Average weekly sales per store: ${overall[2]:,.2f}")
    logger.info(f"   Total sales in dataset: ${overall[3]:,.2f}")
    logger.info(f"   Total orders in dataset: {overall[4]:,}")


def _perform_data_quality_check(session: Session) -> None:
    """Perform and display data quality checks."""
    logger.info("\n7. Data quality check:")
    logger.info("-" * 80)

    quality: Row = session.sql(
        load_sql("preparation/data_quality_check.sql")
    ).collect()[0]

    logger.info(f"   Total snapshots: {quality[0]:,}")
    logger.info(f"   Weeks with zero sales: {quality[1]:,}")
    logger.info(f"   Weeks with zero orders: {quality[2]:,}")
    logger.info(f"   Invalid records (sales but no orders): {quality[3]:,}")

    zero_sales_count: int = cast("int", quality[1])
    if zero_sales_count > 0:
        logger.warning(
            f"\n   WARNING: {zero_sales_count} snapshots have zero sales. Investigating..."
        )
        zero_sales: list[Row] = session.sql(
            load_sql("preparation/zero_sales_investigation.sql")
        ).collect()
        for row in zero_sales:
            logger.warning(f"      {row[0]}: {row[1]} weeks with zero sales")


def _display_recent_snapshots(session: Session, per_store: list[Row]) -> None:
    """Show most recent snapshots for first few stores."""
    logger.info("\n8. Most recent snapshots (last 3 per store):")
    logger.info("-" * 120)

    for store_info in per_store[:3]:  # Show first 3 stores
        store_name: str = cast("str", store_info[0])
        logger.info(f"\n{store_name}:")
        recent_query = load_sql(
            "preparation/recent_snapshots_by_store.sql", store_name=store_name
        )
        recent: list[Row] = session.sql(recent_query).collect()

        logger.info(
            f"{'ID':<8} {'Snapshot (Sunday)':<20} {'Predict Week':<20} "
            f"{'Sales $':<15} {'Orders':<10}"
        )
        logger.info("-" * 80)
        for row in recent:
            logger.info(
                f"{row[0]:<8} {row[1]!s:<20} {row[2]!s:<20} "
                f"${row[3]:<14,.2f} {row[4]:<10,}"
            )


def prepare_weekly_sales_by_store(session: Session) -> None:
    """Prepare data for getML to predict next week's sales from Sunday night, grouped by store.

    Creates:
    - population_weekly_by_store: Weekly snapshots per store at Sunday 23:59:59
    - population_weekly_by_store_with_target: Population table with target column
    - Target: Sum of order_total for the following 7 days for that store
    - Only includes complete weeks (store was open entire week)

    Args:
        session: Active Snowflake Snowpark session
    """
    # Setup and validation
    validate_raw_schema(session)
    _ensure_prepared_schema(session)

    logger.info("=" * 80)
    logger.info("PREPARING WEEKLY SALES FORECASTING DATA BY STORE FOR GETML")
    logger.info("=" * 80)

    # Data preparation pipeline
    _analyze_and_display_stores(session)
    per_store = _create_weekly_population_table(session)
    _add_target_column(session)

    # Display analysis and quality checks
    _display_sample_data(session, per_store)
    _display_store_statistics(session)
    _display_overall_statistics(session)
    _perform_data_quality_check(session)
    _display_recent_snapshots(session, per_store)

    logger.info("\n" + "=" * 80)
    logger.info("DATA PREPARATION COMPLETE!")
    logger.info("=" * 80)
    logger.info("\nTables created in PREPARED schema:")
    logger.info("  - population_weekly_by_store")
    logger.info("  - population_weekly_by_store_with_target (USE THIS FOR GETML)")
    logger.info(
        "\nFor getML integration instructions, see: "
        "docs/GETML_WEEKLY_SALES_DATA_PREPARATION.md"
    )
    logger.info("\n")


if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    # Example usage - requires connection parameters
    logger.info("This module requires a Snowflake session to be passed.")
    logger.info("Example usage:")
    logger.info("""
    from settings import SnowflakeSettings
    from snowflake_session import create_session
    from data import prepare_weekly_sales_by_store

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        prepare_weekly_sales_by_store(session)
    """)
