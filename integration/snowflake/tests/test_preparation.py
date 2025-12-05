"""Tests for data preparation module.

Tests validation logic and pipeline orchestration using mocked
Snowflake sessions.
"""

# pyright: reportAny=false

from unittest.mock import MagicMock

import pytest

from data.preparation import (
    DataPreparationError,
    _validate_source_tables,  # pyright: ignore[reportPrivateUsage]
    create_weekly_sales_by_store_with_target,
)


class TestValidateSourceTables:
    """Tests for source table validation logic."""

    def test_raises_error_when_table_query_fails(self, mock_session: MagicMock) -> None:
        """Verify DataPreparationError raised when required table doesn't exist."""
        mock_session.sql.return_value.collect.side_effect = Exception(
            "Table RAW.raw_stores does not exist"
        )

        with pytest.raises(DataPreparationError, match="Failed to validate"):
            _validate_source_tables(mock_session, "RAW")

    def test_raises_error_when_result_is_empty(self, mock_session: MagicMock) -> None:
        """Verify DataPreparationError raised when table query returns empty result."""
        mock_session.sql.return_value.collect.return_value = []

        with pytest.raises(
            DataPreparationError, match="does not exist or is not accessible"
        ):
            _validate_source_tables(mock_session, "RAW")

    def test_succeeds_when_tables_exist(self, mock_session: MagicMock) -> None:
        """Verify no error when required tables exist and are accessible."""
        mock_session.sql.return_value.collect.return_value = [{"count": 100}]

        _validate_source_tables(mock_session, "RAW")

    def test_uses_provided_source_schema(self, mock_session: MagicMock) -> None:
        """Verify provided source schema is used in validation queries."""
        mock_session.sql.return_value.collect.return_value = [{"count": 100}]

        _validate_source_tables(mock_session, "CUSTOM_SOURCE")

        sql_calls = [c[0][0] for c in mock_session.sql.call_args_list]
        assert all("CUSTOM_SOURCE" in c for c in sql_calls)


class TestCreateWeeklySalesByStoreWithTarget:
    """Tests for the main preparation pipeline."""

    def test_validates_source_tables_first(self, mock_session: MagicMock) -> None:
        """Verify pipeline validates source tables before proceeding."""
        mock_session.sql.return_value.collect.side_effect = Exception(
            "Table does not exist"
        )

        with pytest.raises(DataPreparationError, match="Failed to validate"):
            _ = create_weekly_sales_by_store_with_target(mock_session)
