"""Data operations for getML Feature Store integration with Snowflake.

Usage example:
    from settings import SnowflakeSettings
    from snowflake_session import create_session
    from data import load_jaffle_shop_data, prepare_weekly_sales_by_store

    # Settings auto-load from SNOWFLAKE_* environment variables
    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        load_jaffle_shop_data(session)
        prepare_weekly_sales_by_store(session)
"""

from ._sql_loader import load_sql
from .ingestion import (
    DataIngestionError,
    load_jaffle_shop_data,
    load_single_table,
    rollback_transaction,
)
from .preparation import prepare_weekly_sales_by_store, validate_raw_schema

__all__ = [
    "DataIngestionError",
    "load_jaffle_shop_data",
    "load_single_table",
    "load_sql",
    "prepare_weekly_sales_by_store",
    "rollback_transaction",
    "validate_raw_schema",
]
