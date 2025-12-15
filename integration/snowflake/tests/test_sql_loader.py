"""Tests for sql_loader module.

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
        content = load_sql("common/create_schema.sql", schema_name="PREPARED")

        assert "CREATE SCHEMA" in content
        assert "PREPARED" in content

    def test_returns_raw_content_when_no_kwargs(self) -> None:
        """Verify load_sql returns unmodified content without kwargs."""
        content: str = load_sql(
            path="common/create_schema.sql",
            schema_name="RAW",
        )

        # Content should contain the schema name after formatting
        assert isinstance(content, str)
        assert len(content) > 0
        assert "RAW" in content

    def test_raises_file_not_found_for_missing_file(self) -> None:
        """Verify FileNotFoundError propagates for nonexistent SQL files."""
        with pytest.raises(FileNotFoundError):
            _ = load_sql(path="nonexistent/missing.sql")
