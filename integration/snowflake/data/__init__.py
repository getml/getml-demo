"""Data operations for getML Feature Store integration with Snowflake.

Usage example:
    from settings import SnowflakeSettings
    from snowflake_session import create_session
    from data import (
        load_from_gcs,
        create_weekly_sales_by_store_with_target,
        get_table_names,
    )

    # Settings auto-load from SNOWFLAKE_* environment variables
    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        # Load data from GCS (requires storage integration)
        load_from_gcs(
            session,
            storage_integration="GETML_GCS_INTEGRATION",
        )

        # Prepare weekly sales forecasting data
        population_table = create_weekly_sales_by_store_with_target(
            session,
            table_name="WEEKLY_SALES_BY_STORE_WITH_TARGET",
        )

        # Access tables for Arrow export
        tables = get_table_names("RAW")
        orders_arrow = session.table(tables["orders"]).to_arrow()
        population_arrow = session.table(population_table).to_arrow()
"""

from .ingestion import (
    DEFAULT_GCS_BUCKET,
    JAFFLE_SHOP_TABLE_NAMES,
    DataIngestionError,
    get_table_names,
    load_from_gcs,
    load_from_s3,
)
from .preparation import (
    DEFAULT_POPULATION_TABLE_NAME,
    DataPreparationError,
    create_weekly_sales_by_store_with_target,
)

__all__ = [
    "DEFAULT_GCS_BUCKET",
    "DEFAULT_POPULATION_TABLE_NAME",
    "JAFFLE_SHOP_TABLE_NAMES",
    "DataIngestionError",
    "DataPreparationError",
    "create_weekly_sales_by_store_with_target",
    "get_table_names",
    "load_from_gcs",
    "load_from_s3",
]
