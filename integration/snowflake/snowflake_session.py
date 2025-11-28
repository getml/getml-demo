"""Snowflake session management for getML Feature Store integration.

This module provides factory functions for creating Snowflake Snowpark sessions.
Sessions support the context manager protocol for automatic cleanup.

Usage example:
    from settings import SnowflakeAdminSettings, SnowflakeSettings
    from snowflake_session import create_admin_session, create_session

    # Admin session for bootstrap operations
    with create_admin_session(SnowflakeAdminSettings.from_env()) as session:
        session.sql("CREATE DATABASE IF NOT EXISTS mydb").collect()

    # Full session for data operations
    with create_session(SnowflakeSettings.from_env()) as session:
        session.sql("SELECT * FROM mytable").collect()
"""

import logging

from snowflake.snowpark import Session

from settings import SnowflakeAdminSettings, SnowflakeSettings

logger: logging.Logger = logging.getLogger(__name__)

# TODO: Evaluate single SnowflakeSettings class with optional fields


def create_admin_session(settings: SnowflakeAdminSettings) -> Session:
    """Create a Snowflake session for administrative operations.

    This session connects without specifying warehouse or database,
    allowing creation of those resources during bootstrap.

    Raises:
        SnowflakeSessionError: If connection to Snowflake fails.
    """
    connection_params: dict[str, str | int] = {
        "account": settings.account,
        "user": settings.user,
        "password": settings.password.get_secret_value(),
        "role": settings.role,
    }

    return _create_session(connection_params)


def create_session(settings: SnowflakeSettings) -> Session:
    """Create a Snowflake session for data operations.

    This session connects with full context including warehouse,
    database, and schema for executing queries and loading data.

    Raises:
        SnowflakeSessionError: If connection to Snowflake fails.
    """
    connection_params: dict[str, str | int] = {
        "account": settings.account,
        "user": settings.user,
        "password": settings.password.get_secret_value(),
        "role": settings.role,
        "warehouse": settings.warehouse,
        "database": settings.database,
        "schema": settings.schema_name,
    }

    return _create_session(connection_params)


class SnowflakeSessionError(Exception):
    """Raised when Snowflake session creation fails."""


def _create_session(connection_params: dict[str, str | int]) -> Session:
    """Create a Snowpark session with the given parameters."""
    try:
        return Session.builder.configs(connection_params).create()
    except Exception as e:
        raise SnowflakeSessionError(
            f"Failed to create Snowflake session. "
            f"Account: {connection_params.get('account')}, "
            f"User: {connection_params.get('user')}. "
            f"Error: {e}"
        ) from e
