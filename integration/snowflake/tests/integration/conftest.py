"""Fixtures for integration tests requiring real Snowflake connections.

Provides session-scoped fixtures that:
1. Run cleanup of stale TEST_* schemas before tests
2. Create isolated schemas with TEST_{uuid} prefix for test isolation
3. Clean up test schemas after the test session completes
"""

# ruff: noqa: G004

import logging
import os
import sys
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from pydantic import ValidationError
from snowflake.snowpark import Session

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from settings import SnowflakeSettings
from snowflake_session import create_session
from tests.cleanup_test_schemas import cleanup_test_schemas

logger = logging.getLogger(__name__)


def _snowflake_credentials_available() -> bool:
    """Check if required Snowflake environment variables are set."""
    required_vars: list[str] = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_WAREHOUSE",
        "SNOWFLAKE_DATABASE",
    ]
    return all(os.environ.get(var) for var in required_vars)


@pytest.fixture(scope="session")
def integration_test_id() -> str:
    """Generate unique identifier for this test session.

    Used to create isolated schemas that don't conflict with
    parallel test runs.
    """
    return uuid.uuid4().hex[:8].upper()


@pytest.fixture(scope="session")
def snowflake_settings() -> SnowflakeSettings:
    """Load Snowflake settings from environment variables.

    Skips tests if credentials are not available.
    """
    if not _snowflake_credentials_available():
        pytest.skip("Snowflake credentials not available in environment")

    try:
        return SnowflakeSettings.from_env()
    except ValidationError as e:
        pytest.skip(f"Invalid Snowflake configuration: {e}")


@pytest.fixture(scope="session")
def snowflake_session(
    snowflake_settings: SnowflakeSettings,
    integration_test_id: str,
) -> Generator[Session, None, None]:
    """Create a Snowflake session for integration tests.

    Performs pre-test cleanup of stale TEST_* schemas, then yields
    the session for test use. Post-test cleanup removes schemas
    created during this test session.
    """
    with create_session(snowflake_settings) as session:
        # Pre-test cleanup: remove any stale TEST_* schemas from previous runs
        logger.info("Running pre-test cleanup of stale test schemas...")
        dropped = cleanup_test_schemas(session, snowflake_settings.database)
        if dropped:
            logger.info(f"Pre-test cleanup dropped {len(dropped)} stale schema(s)")

        yield session

        # Post-test cleanup: remove schemas created during this test session
        logger.info(f"Running post-test cleanup for test session {integration_test_id}")
        _ = cleanup_test_schemas(session, snowflake_settings.database)


@pytest.fixture(scope="session")
def test_raw_schema(
    snowflake_session: Session,
    integration_test_id: str,
) -> str:
    """Create an isolated RAW schema for testing data ingestion.

    Creates TEST_RAW_{uuid} schema that is cleaned up after tests.
    """
    schema_name = f"TEST_RAW_{integration_test_id}"

    logger.info(f"Creating test RAW schema: {schema_name}")
    _ = snowflake_session.sql(f"CREATE SCHEMA IF NOT EXISTS {schema_name}").collect()
    _ = snowflake_session.sql(f"USE SCHEMA {schema_name}").collect()

    return schema_name


@pytest.fixture(scope="session")
def test_prepared_schema(
    snowflake_session: Session,
    integration_test_id: str,
) -> str:
    """Create an isolated PREPARED schema for testing data preparation.

    Creates TEST_PREPARED_{uuid} schema that is cleaned up after tests.
    """
    schema_name = f"TEST_PREPARED_{integration_test_id}"

    logger.info(f"Creating test PREPARED schema: {schema_name}")
    _ = snowflake_session.sql(f"CREATE SCHEMA IF NOT EXISTS {schema_name}").collect()

    return schema_name
