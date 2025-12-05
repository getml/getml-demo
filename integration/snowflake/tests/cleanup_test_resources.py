"""Cleanup utility for test resources in Snowflake.

Drops test databases (JAFFLE_SHOP_TEST_*) and test schemas (TEST_*) created
by integration tests. Can be run standalone or imported by test fixtures for
pre/post-test cleanup.

Usage:
    # Standalone execution
    uv run python tests/cleanup_test_resources.py

    # Import in fixtures
    from tests.cleanup_test_resources import cleanup_test_databases
    cleanup_test_databases(session)
"""

# ruff: noqa: G004, S608, PLC0415

import logging
import sys
from pathlib import Path

from snowflake.snowpark import Row, Session

logger: logging.Logger = logging.getLogger(__name__)

TEST_DATABASE_PREFIX = "JAFFLE_SHOP_TEST_"
TEST_SCHEMA_PREFIX = "TEST_"


def cleanup_test_databases(session: Session) -> list[str]:
    """Drop all databases with JAFFLE_SHOP_TEST_ prefix.

    Args:
        session: Active Snowflake session with appropriate privileges.

    Returns:
        List of dropped database names.
    """
    result: list[Row] = session.sql(f"""
        SELECT DATABASE_NAME
        FROM INFORMATION_SCHEMA.DATABASES
        WHERE DATABASE_NAME LIKE '{TEST_DATABASE_PREFIX}%'
    """).collect()

    dropped_databases: list[str] = []

    for row in result:
        db_name = str(row["DATABASE_NAME"])  # pyright: ignore[reportUnknownArgumentType]
        _ = session.sql(f"DROP DATABASE IF EXISTS {db_name} CASCADE").collect()
        dropped_databases.append(db_name)
        logger.info(f"Dropped database: {db_name}")

    return dropped_databases


def cleanup_test_schemas(session: Session, database: str | None = None) -> list[str]:
    """Drop all schemas with TEST_ prefix in the specified database.

    Args:
        session: Active Snowflake session.
        database: Database to clean. If None, uses session's current database.

    Returns:
        List of dropped schema names.
    """
    if database:
        _ = session.sql(f"USE DATABASE {database}").collect()

    result: list[Row] = session.sql(f"""
        SELECT SCHEMA_NAME
        FROM INFORMATION_SCHEMA.SCHEMATA
        WHERE SCHEMA_NAME LIKE '{TEST_SCHEMA_PREFIX}%'
    """).collect()

    dropped_schemas: list[str] = []

    for row in result:
        schema_name = str(row["SCHEMA_NAME"])  # pyright: ignore[reportUnknownArgumentType]
        _ = session.sql(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE").collect()
        dropped_schemas.append(schema_name)
        logger.info(f"Dropped schema: {schema_name}")

    return dropped_schemas


def main() -> None:
    """Run cleanup as standalone script."""
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from data import SnowflakeSettings, create_session

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting test resource cleanup...")

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        # Clean up test databases first
        dropped_dbs: list[str] = cleanup_test_databases(session)
        if dropped_dbs:
            logger.info(f"Dropped {len(dropped_dbs)} test database(s).")

        # Also clean up any stray test schemas in the main database
        dropped_schemas: list[str] = cleanup_test_schemas(session, settings.database)
        if dropped_schemas:
            logger.info(f"Dropped {len(dropped_schemas)} test schema(s).")

        if not dropped_dbs and not dropped_schemas:
            logger.info("No test resources found to clean up.")
        else:
            logger.info("Cleanup complete.")


if __name__ == "__main__":
    main()
