"""Snowflake authentication and connection settings.

Provides typed configuration that automatically loads from environment
variables with the SNOWFLAKE_ prefix.

Usage example:
    from data import SnowflakeSettings, create_session

    # Auto-loads from SNOWFLAKE_* environment variables
    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        session.sql("SELECT 1").collect()
"""

from typing import ClassVar, Self

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class SnowflakeSettings(BaseSettings):
    """Settings for Snowflake operations.

    Core fields (account, user, password, role) are required for all connections.
    Optional fields (warehouse, database, schema_name) can be omitted for
    administrative operations like creating warehouses or databases.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="SNOWFLAKE_",
        case_sensitive=False,
    )

    account: str
    user: str
    password: SecretStr
    role: str
    warehouse: str
    database: str
    # Can't use field name "schema" (Pydantic reserved);
    # validation_alias maps standard SNOWFLAKE_SCHEMA env var to this field
    schema_name: str = Field(
        validation_alias="SNOWFLAKE_SCHEMA",
    )

    @classmethod
    def from_env(cls) -> Self:
        """Create settings instance from environment variables.

        Loads configuration from SNOWFLAKE_* environment variables.
        """
        return cls.model_validate({})
