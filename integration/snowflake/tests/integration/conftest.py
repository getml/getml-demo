"""Fixtures for integration tests requiring real Snowflake connections.

Provides session-scoped fixtures that:
1. Run cleanup of stale JAFFLE_SHOP_TEST_* databases before tests
2. Create an isolated test database (JAFFLE_SHOP_TEST_{uuid}) for test isolation
3. Configure storage access for cloud bucket with Parquet files
4. Clean up test database after the test session completes

Storage Configuration:
- GCS (default): Uses HTTPS to fetch files from gs://static.getml.com/datasets/jaffle_shop/
  No credentials or storage integration required.
- S3: Set S3_BUCKET_URL to a public S3 bucket with Parquet files
  (e.g., s3://your-bucket/jaffle_shop/)
"""

# ruff: noqa: G004

import logging
import os
import sys
import uuid
from collections.abc import Generator
from enum import Enum
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic.dataclasses import dataclass
from snowflake.snowpark import Session

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data import (
    DEFAULT_GCS_BUCKET,
    SnowflakeSettings,
    create_session,
    load_from_gcs,
    load_from_s3,
)
from tests.cleanup_test_resources import cleanup_test_databases

logger = logging.getLogger(__name__)


class CloudProvider(Enum):
    """Supported cloud storage providers for data ingestion."""

    GCS = "gcs"
    S3 = "s3"


@dataclass(frozen=True)
class StorageConfig:
    """Configuration for cloud storage access in integration tests.

    Encapsulates the parameters needed to call either load_from_gcs or
    load_from_s3, providing a unified interface for test fixtures.
    """

    provider: CloudProvider
    bucket_url: str


def load_jaffle_shop_data(
    session: Session,
    config: StorageConfig,
) -> dict[str, int]:
    """Load Jaffle Shop data using the appropriate loader for the storage provider.

    Dispatches to load_from_gcs or load_from_s3 based on the config's provider.
    """
    if config.provider == CloudProvider.GCS:
        return load_from_gcs(session, bucket=config.bucket_url)
    return load_from_s3(session, bucket=config.bucket_url)


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


def _get_storage_config() -> StorageConfig:
    """Build StorageConfig from environment variables.

    Priority:
    1. S3 public bucket if S3_BUCKET_URL is set
    2. GCS (default) - uses HTTPS, no credentials required

    Returns:
        StorageConfig with appropriate provider and bucket URL.
    """
    s3_bucket_url = os.environ.get("S3_BUCKET_URL")
    if s3_bucket_url:
        return StorageConfig(
            provider=CloudProvider.S3,
            bucket_url=s3_bucket_url,
        )

    # Default: GCS via HTTPS (no credentials required)
    return StorageConfig(
        provider=CloudProvider.GCS,
        bucket_url=DEFAULT_GCS_BUCKET,
    )


@pytest.fixture(scope="session")
def integration_test_id() -> str:
    """Generate unique identifier for this test session.

    Used to create an isolated test database that doesn't conflict
    with parallel test runs.
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
def storage_config() -> StorageConfig:
    """Create StorageConfig for cloud storage access.

    By default, uses GCS which fetches files via HTTPS - no credentials needed.
    To use S3 instead, set S3_BUCKET_URL environment variable.
    """
    return _get_storage_config()


@pytest.fixture(scope="session")
def test_database(
    snowflake_settings: SnowflakeSettings,
    integration_test_id: str,
) -> Generator[str, None, None]:
    """Create an isolated test database for this test session.

    Creates JAFFLE_SHOP_TEST_{uuid} database that is cleaned up after tests.
    This provides complete isolation from production data.
    """
    db_name = f"JAFFLE_SHOP_TEST_{integration_test_id}"

    with create_session(snowflake_settings) as session:
        # Pre-test cleanup: remove any stale test databases from previous runs
        logger.info("Running pre-test cleanup of stale test databases...")
        dropped = cleanup_test_databases(session)
        if dropped:
            logger.info(f"Pre-test cleanup dropped {len(dropped)} stale database(s)")

        # Create the test database
        logger.info(f"Creating test database: {db_name}")
        _ = session.sql(f"CREATE DATABASE IF NOT EXISTS {db_name}").collect()

        yield db_name

        # Post-test cleanup: drop the test database
        logger.info(f"Dropping test database: {db_name}")
        _ = session.sql(f"DROP DATABASE IF EXISTS {db_name} CASCADE").collect()


@pytest.fixture(scope="session")
def snowflake_session(
    snowflake_settings: SnowflakeSettings,
    test_database: str,
) -> Generator[Session, None, None]:
    """Create a Snowflake session for integration tests using the test database.

    The session is configured to use the isolated test database where RAW and
    PREPARED schemas can be created without affecting production data.
    """
    with create_session(snowflake_settings) as session:
        # Switch to the test database
        logger.info(f"Using test database: {test_database}")
        _ = session.sql(f"USE DATABASE {test_database}").collect()

        yield session
