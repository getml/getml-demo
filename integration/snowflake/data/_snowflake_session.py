"""Snowflake session management for getML Feature Store integration.

This module provides a factory function for creating Snowflake Snowpark sessions.
Sessions support the context manager protocol for automatic cleanup.

Usage example:
    from data import SnowflakeSettings, create_session

    with create_session(SnowflakeSettings.from_env()) as session:
        session.sql("SELECT * FROM mytable").collect()
"""

import logging

from snowflake.snowpark import Session
from snowflake.snowpark.exceptions import SnowparkSessionException

from ._settings import SnowflakeSettings

logger: logging.Logger = logging.getLogger(__name__)


def create_session(settings: SnowflakeSettings) -> Session:
    """Create a Snowflake Snowpark session.

    Connects using the provided settings.

    Raises:
        SnowparkSessionException: If connection to Snowflake fails.
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

    return _establish_session(connection_params)


def _establish_session(connection_params: dict[str, str | int]) -> Session:
    """Create a Snowpark session with the given parameters."""
    try:
        return Session.builder.configs(connection_params).create()
    except Exception as e:
        raise SnowparkSessionException(
            f"Failed to create Snowflake session. "
            f"Account: {connection_params.get('account')}, "
            f"User: {connection_params.get('user')}. "
            f"Error: {e}"
        ) from e
