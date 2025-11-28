"""Snowflake connection settings using pydantic-settings.

Provides typed configuration classes that automatically load from environment
variables with the SNOWFLAKE_ prefix.

Usage example:
    from settings import SnowflakeAdminSettings, SnowflakeSettings

    # Auto-loads from SNOWFLAKE_* environment variables
    admin_settings = SnowflakeAdminSettings.from_env()
    full_settings = SnowflakeSettings.from_env()
"""

from typing import ClassVar, Self

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SNOWFLAKE_ROLE = "ACCOUNTADMIN"
DEFAULT_SNOWFLAKE_SCHEMA = "RAW"


class SnowflakeAdminSettings(BaseSettings):
    """Settings for administrative Snowflake operations (bootstrap).

    These minimal settings allow connecting without specifying warehouse
    or database, which is required for creating those resources.
    """

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix="SNOWFLAKE_",
        case_sensitive=False,
    )

    account: str
    user: str
    password: SecretStr
    role: str = DEFAULT_SNOWFLAKE_ROLE

    @classmethod
    def from_env(cls) -> Self:
        """Create settings instance from environment variables.

        Loads configuration from SNOWFLAKE_* environment variables.
        """
        return cls.model_validate({})


class SnowflakeSettings(SnowflakeAdminSettings):
    """Full settings for Snowflake data operations.

    Extends admin settings with warehouse, database, and schema
    required for executing queries and loading data.
    """

    warehouse: str
    database: str
    schema_name: str = Field(
        default=DEFAULT_SNOWFLAKE_SCHEMA,
        validation_alias="SNOWFLAKE_SCHEMA",
    )
