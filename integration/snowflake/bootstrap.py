"""Bootstrap Snowflake infrastructure for the Jaffle Shop dataset.

Creates the required warehouse, database, and optionally GCS storage integration.
All operations are idempotent using CREATE ... IF NOT EXISTS / CREATE OR REPLACE.

Usage example:
    from settings import SnowflakeSettings
    from snowflake_session import create_session
    from bootstrap import bootstrap_snowflake_infrastructure

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        bootstrap_snowflake_infrastructure(session, settings)

For GCS storage integration setup:
    from bootstrap import setup_gcs_storage_integration

    with create_session(settings) as session:
        info = setup_gcs_storage_integration(session)
        # Follow printed instructions to grant IAM permissions in GCP
"""

# ruff: noqa: G004, T201

from __future__ import annotations

import logging
from dataclasses import dataclass

from snowflake.snowpark import Row, Session

from settings import SnowflakeSettings
from sql_loader import load_sql

logger: logging.Logger = logging.getLogger(__name__)

WAREHOUSE_SIZE = "X-SMALL"
AUTO_SUSPEND_SECONDS = 60

DEFAULT_GCS_ALLOWED_LOCATION = "gcs://static.getml.com/datasets/"
DEFAULT_INTEGRATION_NAME = "GETML_GCS_INTEGRATION"


class BootstrapError(Exception):
    """Raised when bootstrap operations fail."""


@dataclass
class StorageIntegrationInfo:
    """Information about a GCS storage integration.

    Attributes:
        name: Integration name.
        enabled: Whether the integration is enabled.
        allowed_locations: GCS locations the integration can access.
        service_account: GCS service account to grant IAM permissions to.
    """

    name: str
    enabled: bool
    allowed_locations: str
    service_account: str


# =============================================================================
# Internal Helpers
# =============================================================================


def _extract_bucket_name(gcs_url: str) -> str:
    """Extract bucket name from GCS URL."""
    url = gcs_url.lower().replace("gcs://", "").replace("gs://", "")
    return url.split("/")[0]


def _print_gcp_setup_guide(
    info: StorageIntegrationInfo,
    bucket_name: str,
) -> None:
    """Print actionable GCP setup instructions after integration creation."""
    print(f"""
======================================================================
GCS STORAGE INTEGRATION CREATED
======================================================================

Integration:     {info.name}
Service Account: {info.service_account}

----------------------------------------------------------------------
REQUIRED: Grant IAM permissions in GCP
----------------------------------------------------------------------

Run this command to grant read access:

  gsutil iam ch \\
    serviceAccount:{info.service_account}:objectViewer \\
    gs://{bucket_name}

----------------------------------------------------------------------
Then retry the data loading operation.
----------------------------------------------------------------------

======================================================================
""")


# =============================================================================
# Core Bootstrap Functions
# =============================================================================


def bootstrap_snowflake_infrastructure(
    session: Session,
    settings: SnowflakeSettings,
) -> None:
    """Create Snowflake warehouse and database if they don't exist.

    Raises:
        BootstrapError: If warehouse or database creation fails.
    """
    _create_warehouse(session, warehouse_name=settings.warehouse)
    _create_database(session, database_name=settings.database)
    logger.info("✓ Snowflake infrastructure bootstrap complete")


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


# =============================================================================
# GCS Storage Integration Setup
# =============================================================================


def setup_gcs_storage_integration(
    session: Session,
    integration_name: str = DEFAULT_INTEGRATION_NAME,
    allowed_location: str = DEFAULT_GCS_ALLOWED_LOCATION,
) -> StorageIntegrationInfo:
    """Create GCS storage integration and display required GCP setup commands.

    Creates the Snowflake storage integration for GCS access and prints
    the gcloud commands needed to grant IAM permissions.

    Requires ACCOUNTADMIN role or CREATE INTEGRATION privilege.

    Args:
        session: Active Snowflake Snowpark session.
        integration_name: Name for the storage integration.
        allowed_location: GCS path prefix to allow access to.

    Returns:
        StorageIntegrationInfo with the service account for IAM setup.

    Raises:
        BootstrapError: If integration creation fails.
    """
    logger.info(f"Creating GCS storage integration '{integration_name}'...")

    try:
        sql: str = load_sql(
            path="bootstrap/create_storage_integration_gcs.sql",
            integration_name=integration_name,
            allowed_location=allowed_location,
        )
        _ = session.sql(query=sql).collect()
    except Exception as e:
        raise BootstrapError(
            f"Failed to create storage integration. "
            f"Ensure you have ACCOUNTADMIN role. Error: {e}"
        ) from e

    logger.info(f"✓ Storage integration '{integration_name}' created")

    info: StorageIntegrationInfo = get_storage_integration_info(
        session, integration_name
    )
    bucket_name: str = _extract_bucket_name(gcs_url=allowed_location)
    _print_gcp_setup_guide(info, bucket_name)

    return info


def get_storage_integration_info(
    session: Session,
    integration_name: str = DEFAULT_INTEGRATION_NAME,
) -> StorageIntegrationInfo:
    """Retrieve details about an existing storage integration.

    Args:
        session: Active Snowflake Snowpark session.
        integration_name: Name of the storage integration.

    Returns:
        StorageIntegrationInfo with integration details.

    Raises:
        BootstrapError: If integration doesn't exist or query fails.
    """
    try:
        sql: str = load_sql(
            path="bootstrap/describe_storage_integration.sql",
            integration_name=integration_name,
        )
        rows: list[Row] = session.sql(query=sql).collect()
    except Exception as e:
        raise BootstrapError(
            f"Storage integration '{integration_name}' not found. "
            f"Run setup_gcs_storage_integration() first. Error: {e}"
        ) from e

    properties: dict[str, str] = {
        str(row["property"]): str(row["property_value"])  # pyright: ignore[reportUnknownArgumentType]
        for row in rows
    }

    return StorageIntegrationInfo(
        name=integration_name,
        enabled=properties.get("ENABLED", "").lower() == "true",
        allowed_locations=properties.get("STORAGE_ALLOWED_LOCATIONS", ""),
        service_account=properties.get("STORAGE_GCP_SERVICE_ACCOUNT", ""),
    )


def validate_storage_integration(
    session: Session,
    integration_name: str = DEFAULT_INTEGRATION_NAME,
    storage_path: str = DEFAULT_GCS_ALLOWED_LOCATION,
) -> str:
    """Validate a storage integration can list files in GCS.

    Uses Snowflake's native SYSTEM$VALIDATE_STORAGE_INTEGRATION function
    with the 'list' action to verify read permissions on the storage path.

    Args:
        session: Active Snowflake Snowpark session.
        integration_name: Name of the storage integration.
        storage_path: GCS path to validate access to (must be within
            the integration's STORAGE_ALLOWED_LOCATIONS).

    Returns:
        JSON string with validation status and action results.

    Raises:
        BootstrapError: If validation fails or permissions are insufficient.
    """
    logger.info(f"Validating storage integration '{integration_name}'...")

    try:
        sql: str = load_sql(
            path="bootstrap/validate_storage_integration.sql",
            integration_name=integration_name,
            storage_path=storage_path,
            test_file="validation_test.tmp",
        )
        rows: list[Row] = session.sql(sql).collect()
    except Exception as e:
        raise BootstrapError(
            f"Storage integration validation failed. Error: {e}"
        ) from e
    else:
        result = str(rows[0]["VALIDATION_RESULT"]) if rows else "No result"  # pyright: ignore[reportUnknownArgumentType]
        logger.info(f"Validation result: {result}")
        return result


# Re-export for external usage
__all__ = [
    "BootstrapError",
    "StorageIntegrationInfo",
    "bootstrap_snowflake_infrastructure",
    "get_storage_integration_info",
    "setup_gcs_storage_integration",
    "validate_storage_integration",
]
