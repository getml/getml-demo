"""Tests for data package utilities.

Tests the load_sql function which handles SQL file loading
and parameter substitution.
"""

# pyright: reportAny=false

import pytest

from data import load_sql


class TestLoadSql:
    """Tests for load_sql utility function."""

    def test_loads_existing_sql_file(self) -> None:
        """Verify load_sql reads content from existing SQL file."""
        content = load_sql("preparation/create_prepared_schema.sql")

        assert "CREATE SCHEMA" in content
        assert "PREPARED" in content

    def test_applies_formatting_when_kwargs_provided(self) -> None:
        """Verify load_sql applies string formatting with provided kwargs."""
        content = load_sql(
            "preparation/sample_data_by_store.sql",
            store_name="Test Store",
        )

        assert "Test Store" in content

    def test_returns_raw_content_when_no_kwargs(self) -> None:
        """Verify load_sql returns unmodified content without kwargs."""
        content = load_sql("ingestion/create_raw_schema.sql")

        # Content should contain the placeholder syntax if any exist,
        # or just be the raw SQL
        assert isinstance(content, str)
        assert len(content) > 0

    def test_raises_file_not_found_for_missing_file(self) -> None:
        """Verify FileNotFoundError propagates for nonexistent SQL files."""
        with pytest.raises(FileNotFoundError):
            _ = load_sql("nonexistent/missing.sql")

    def test_preserves_placeholders_when_no_kwargs(self) -> None:
        """Verify load_sql preserves {placeholders} when no kwargs provided."""
        # sample_data_by_store.sql has {store_name} placeholder
        content: str = load_sql("preparation/sample_data_by_store.sql")

        # Placeholder should remain in the content
        assert "{store_name}" in content
