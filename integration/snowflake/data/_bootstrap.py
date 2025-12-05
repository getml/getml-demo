"""Bootstrap Snowflake infrastructure for the Jaffle Shop dataset.

Creates the required warehouse and database.
All operations are idempotent using CREATE ... IF NOT EXISTS.

The main entry point is `ensure_infrastructure()` which auto-detects and creates
missing resources. It is called automatically by data loading functions when
settings are provided.

Usage example:
    from data import SnowflakeSettings, create_session, ensure_infrastructure

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        ensure_infrastructure(session, settings)
        # Warehouse and database are now guaranteed to exist
"""

# ruff: noqa: G004

from __future__ import annotations

import logging

from snowflake.snowpark import Row, Session
from snowflake.snowpark.exceptions import SnowparkSQLException

from ._settings import SnowflakeSettings
from ._sql_loader import load_sql

logger: logging.Logger = logging.getLogger(__name__)

WAREHOUSE_SIZE = "X-SMALL"
AUTO_SUSPEND_SECONDS = 60


class BootstrapError(Exception):
    """Raised when bootstrap operations fail."""


# =============================================================================
# Internal Helpers
# =============================================================================


def _warehouse_exists(session: Session, warehouse_name: str) -> bool:
    """Check if a warehouse exists.

    Args:
        session: Active Snowflake Snowpark session.
        warehouse_name: Name of the warehouse to check.

    Returns:
        True if warehouse exists, False otherwise.
    """
    try:
        rows: list[Row] = session.sql(
            f"SHOW WAREHOUSES LIKE '{warehouse_name}'"
        ).collect()
        return len(rows) > 0
    except SnowparkSQLException:
        return False


def _database_exists(session: Session, database_name: str) -> bool:
    """Check if a database exists.

    Args:
        session: Active Snowflake Snowpark session.
        database_name: Name of the database to check.

    Returns:
        True if database exists, False otherwise.
    """
    try:
        rows: list[Row] = session.sql(
            f"SHOW DATABASES LIKE '{database_name}'"
        ).collect()
        return len(rows) > 0
    except SnowparkSQLException:
        return False


# =============================================================================
# Core Bootstrap Functions
# =============================================================================


def ensure_infrastructure(
    session: Session,
    settings: SnowflakeSettings,
) -> None:
    """Ensure warehouse and database exist, creating if missing.

    This is the main entry point for auto-bootstrapping. It checks if the
    warehouse and database specified in settings exist, and creates them
    if they don't. All operations are idempotent.

    Args:
        session: Active Snowflake Snowpark session.
        settings: Settings containing warehouse and database names.

    Raises:
        BootstrapError: If required settings are missing or if resource
            creation fails (e.g., due to insufficient privileges).

    Example:
        from data import SnowflakeSettings, create_session, ensure_infrastructure

        settings = SnowflakeSettings.from_env()
        with create_session(settings) as session:
            ensure_infrastructure(session, settings)
            # Warehouse and database are now guaranteed to exist
    """
    if not settings.warehouse:
        raise BootstrapError("warehouse must be specified in settings for bootstrap")
    if not settings.database:
        raise BootstrapError("database must be specified in settings for bootstrap")

    warehouse_ready = _warehouse_exists(session, settings.warehouse)
    database_ready = _database_exists(session, settings.database)

    if warehouse_ready and database_ready:
        logger.debug(
            "Infrastructure already exists: warehouse=%s, database=%s",
            settings.warehouse,
            settings.database,
        )
        return

    try:
        if not warehouse_ready:
            _create_warehouse(session, warehouse_name=settings.warehouse)
        if not database_ready:
            _create_database(session, database_name=settings.database)
        logger.info("Snowflake infrastructure ready")
    except Exception as e:
        raise BootstrapError(
            "Cannot create Snowflake infrastructure. "
            "Your current role may lack CREATE WAREHOUSE or CREATE DATABASE "
            "privilege.\n\n"
            "Options:\n"
            "  1. Ask an administrator to create the warehouse and database\n"
            "  2. Switch to a role with CREATE WAREHOUSE/DATABASE privilege "
            "(e.g., ACCOUNTADMIN)\n"
            "  3. Create resources manually before running the pipeline\n\n"
            f"Original error: {e}"
        ) from e


def _create_warehouse(session: Session, warehouse_name: str) -> None:
    """Create warehouse with X-SMALL size and auto-suspend enabled."""
    logger.info(f"Creating warehouse '{warehouse_name}' if not exists...")

    sql: str = load_sql(
        path="bootstrap/create_warehouse.sql",
        warehouse_name=warehouse_name,
        warehouse_size=WAREHOUSE_SIZE,
        auto_suspend_seconds=str(AUTO_SUSPEND_SECONDS),
    )
    _ = session.sql(query=sql).collect()

    logger.info(f"✓ Warehouse '{warehouse_name}' ready")


def _create_database(session: Session, database_name: str) -> None:
    """Create database if it doesn't exist."""
    logger.info(f"Creating database '{database_name}' if not exists...")

    sql: str = load_sql(
        path="bootstrap/create_database.sql", database_name=database_name
    )
    _ = session.sql(query=sql).collect()

    logger.info(f"✓ Database '{database_name}' ready")


__all__ = [
    "BootstrapError",
    "ensure_infrastructure",
]
