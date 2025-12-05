"""Data operations for getML Feature Store integration with Snowflake.

When settings are provided to data loading and preparation functions,
infrastructure (warehouse, database) is automatically bootstrapped if needed.

Usage example:
    from data import (
        SnowflakeSettings,
        create_session,
        ingestion,
        preparation,
    )

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        ingestion.load_from_gcs(session, settings=settings)
        preparation.create_weekly_sales_by_store_with_target(session, settings=settings)
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
    "load_from_gcs",
    "load_from_s3",
    "load_sql",
]
