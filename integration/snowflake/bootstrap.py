"""Bootstrap Snowflake infrastructure for the Jaffle Shop dataset.

Creates the required warehouse and database if they don't exist.
All operations are idempotent using CREATE ... IF NOT EXISTS.

Usage example:
    from settings import SnowflakeAdminSettings, SnowflakeSettings
    from snowflake_session import create_admin_session
    from bootstrap import bootstrap_snowflake_infrastructure

    admin_settings = SnowflakeAdminSettings.from_env()
    full_settings = SnowflakeSettings.from_env()

    with create_admin_session(admin_settings) as session:
        bootstrap_snowflake_infrastructure(session, full_settings)
"""

# ruff: noqa: G004

import logging

from snowflake.snowpark import Session

from data import load_sql
from settings import SnowflakeSettings

logger: logging.Logger = logging.getLogger(__name__)

WAREHOUSE_SIZE = "X-SMALL"
AUTO_SUSPEND_SECONDS = 60


def bootstrap_snowflake_infrastructure(
    session: Session,
    settings: SnowflakeSettings,
) -> None:
    """Create Snowflake warehouse and database if they don't exist.

    Raises:
        Exception: If warehouse or database creation fails.
    """
    _create_warehouse(session, settings.warehouse)
    _create_database(session, settings.database)
    logger.info("Snowflake infrastructure bootstrap complete")


def _create_warehouse(session: Session, warehouse_name: str) -> None:
    """Create warehouse with X-SMALL size and auto-suspend enabled."""
    logger.info(f"Creating warehouse '{warehouse_name}' if not exists...")

    sql = load_sql(
        "bootstrap/create_warehouse.sql",
        warehouse_name=warehouse_name,
        warehouse_size=WAREHOUSE_SIZE,
        auto_suspend_seconds=str(AUTO_SUSPEND_SECONDS),
    )
    _ = session.sql(sql).collect()

    logger.info(f"✓ Warehouse '{warehouse_name}' ready")


def _create_database(session: Session, database_name: str) -> None:
    """Create database if it doesn't exist."""
    logger.info(f"Creating database '{database_name}' if not exists...")

    sql = load_sql("bootstrap/create_database.sql", database_name=database_name)
    _ = session.sql(sql).collect()

    logger.info(f"✓ Database '{database_name}' ready")
