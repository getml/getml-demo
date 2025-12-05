"""Data operations for getML Feature Store integration with Snowflake.

When settings are provided to data loading and preparation functions,
infrastructure (warehouse, database) is automatically bootstrapped if needed.

Usage example:
    from data import (
        SnowflakeSettings,
        create_session,
        load_from_gcs,
        create_weekly_sales_by_store_with_target,
        get_table_names,
    )

    # Settings auto-load from SNOWFLAKE_* environment variables
    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        # Load data from GCS - auto-bootstraps warehouse + database
        # No GCP credentials required - files are fetched via HTTPS
        load_from_gcs(session, settings=settings)

        # Prepare weekly sales forecasting data
        population_table = create_weekly_sales_by_store_with_target(
            session,
            settings=settings,
        )

        # Access tables for Arrow export
        tables = get_table_names("RAW")
        orders_arrow = session.table(tables["orders"]).to_arrow()
        population_arrow = session.table(population_table).to_arrow()
"""

from snowflake.snowpark.exceptions import SnowparkSessionException

from ._bootstrap import (
    BootstrapError,
    ensure_infrastructure,
)
from ._settings import SnowflakeSettings
from ._snowflake_session import create_session
from ._sql_loader import load_sql
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
    "BootstrapError",
    "DataIngestionError",
    "DataPreparationError",
    "SnowflakeSettings",
    "SnowparkSessionException",
    "create_session",
    "create_weekly_sales_by_store_with_target",
    "ensure_infrastructure",
    "get_table_names",
    "load_from_gcs",
    "load_from_s3",
    "load_sql",
]
