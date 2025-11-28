"""Tests for data preparation module.

Tests validation logic and pipeline orchestration using mocked
Snowflake sessions.
"""

# pyright: reportAny=false

from unittest.mock import MagicMock

import pytest

from data.preparation import prepare_weekly_sales_by_store, validate_raw_schema


class TestValidateRawSchema:
    """Tests for RAW schema validation logic."""

    def test_raises_value_error_when_table_query_fails(
        self, mock_session: MagicMock
    ) -> None:
        """Verify ValueError raised when required table doesn't exist."""
        mock_session.sql.return_value.collect.side_effect = Exception(
            "Table RAW.raw_stores does not exist"
        )

        with pytest.raises(ValueError, match="Failed to validate RAW schema"):
            validate_raw_schema(mock_session)

    def test_raises_value_error_when_result_is_empty(
        self, mock_session: MagicMock
    ) -> None:
        """Verify ValueError raised when table query returns empty result."""
        mock_session.sql.return_value.collect.return_value = []

        with pytest.raises(ValueError, match="does not exist or is not accessible"):
            validate_raw_schema(mock_session)

    def test_succeeds_when_tables_exist(self, mock_session: MagicMock) -> None:
        """Verify no error when required tables exist and are accessible."""
        mock_session.sql.return_value.collect.return_value = [{"count": 100}]

        # Should not raise
        validate_raw_schema(mock_session)


class TestPrepareWeeklySalesByStore:
    """Tests for the main preparation pipeline."""

    def test_validates_raw_schema_first(self, mock_session: MagicMock) -> None:
        """Verify pipeline validates RAW schema before proceeding."""
        mock_session.sql.return_value.collect.side_effect = Exception(
            "Table does not exist"
        )

        with pytest.raises(ValueError, match="RAW schema"):
            prepare_weekly_sales_by_store(mock_session)
