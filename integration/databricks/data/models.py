"""Data models for Databricks integration.

This module provides validated data models for working with Databricks schemas and tables.
All models use Pydantic for validation and are frozen (immutable) by default.
"""

from __future__ import annotations

import re
from typing import Annotated, ClassVar, Final

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

_IDENTIFIER_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_sql_identifier(value: str) -> str:
    """
    Validate SQL identifier to prevent injection attacks.

    Args:
        value: Identifier to validate.

    Returns:
        The validated identifier.

    Raises:
        ValueError: If identifier contains invalid characters.
    """
    if not _IDENTIFIER_PATTERN.fullmatch(value):
        msg = (
            f"Invalid SQL identifier {value!r}. "
            f"Must match pattern: {_IDENTIFIER_PATTERN.pattern!r}"
        )
        raise ValueError(msg)

    return value


# Type alias for validated SQL identifiers (parse-don't-validate)
SqlIdentifier = Annotated[str, AfterValidator(_validate_sql_identifier)]


class SchemaLocation(BaseModel):
    """Location identifier for a Databricks schema."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    catalog: SqlIdentifier
    schema_: SqlIdentifier = Field(alias="schema")

    @property
    def qualified_name(self) -> str:
        """Return fully qualified schema name."""
        return f"{self.catalog}.{self.schema_}"


class TableLocation(BaseModel):
    """Location identifier for a Delta table in Databricks."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    table_name: SqlIdentifier
    location: SchemaLocation

    @property
    def qualified_name(self) -> str:
        """Return fully qualified table name (catalog.schema.table)."""
        return f"{self.location.qualified_name}.{self.table_name}"


class IngestionTableConfig(BaseModel):
    """Configuration for ingesting a table from URL to Delta Lake."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    source_url: str
    destination: TableLocation

    @property
    def full_table_name(self) -> str:
        """Return fully qualified table name."""
        return self.destination.qualified_name
