"""Cleanup utility for test schemas in Snowflake.

Drops all TEST_* schemas created by integration tests. Can be run standalone
or imported by test fixtures for pre/post-test cleanup.

Usage:
    # Standalone execution
    uv run python tests/cleanup_test_schemas.py

    # Import in fixtures
    from tests.cleanup_test_schemas import cleanup_test_schemas
    cleanup_test_schemas(session)
"""

# ruff: noqa: G004, S608, PLC0415

import logging
import sys
from pathlib import Path

from snowflake.snowpark import Row, Session

logger: logging.Logger = logging.getLogger(__name__)

TEST_SCHEMA_PREFIX = "TEST_"


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

    # Get all schemas with TEST_ prefix (prefix is a constant, not user input)
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
    # Add project root to path for imports when run standalone
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from settings import SnowflakeSettings
    from snowflake_session import create_session

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    logger.info("Starting test schema cleanup...")

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        dropped: list[str] = cleanup_test_schemas(session, settings.database)

        if dropped:
            logger.info(f"Cleanup complete. Dropped {len(dropped)} test schema(s).")
        else:
            logger.info("No test schemas found to clean up.")


if __name__ == "__main__":
    main()
