"""Data models for Databricks integration.

This module provides validated data models for working with Databricks schemas and tables.
All models use Pydantic for validation and are frozen (immutable) by default.
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from sqlglot import exp


def _quote_identifier(raw_identifier: str, dialect: str = "databricks") -> str:
    """Quote SQL identifier using sqlglot.

    Args:
        raw_identifier: Identifier to quote.
        dialect: SQL dialect (default: databricks).

    Returns:
        Properly quoted identifier for the target dialect.
    """
    return exp.to_identifier(raw_identifier).sql(dialect=dialect)  # pyright: ignore[reportUnknownMemberType]


SqlIdentifier = Annotated[str, AfterValidator(_quote_identifier)]


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
