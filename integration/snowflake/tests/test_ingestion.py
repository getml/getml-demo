"""Tests for data ingestion module.

Tests error handling, rollback behavior, and successful data loading
orchestration logic using mocked Snowflake sessions.
"""

# pyright: reportAny=false

from unittest.mock import MagicMock

import pytest

from data.ingestion import (
    DataIngestionError,
    load_jaffle_shop_data,
    load_single_table,
    rollback_transaction,
)


class TestLoadJaffleShopData:
    """Tests for the main load_jaffle_shop_data orchestration function."""

    def test_returns_dict_with_all_table_names_on_success(
        self, mock_session: MagicMock
    ) -> None:
        """Verify successful load returns dict mapping table names to row counts."""
        # Configure mock to return appropriate responses for different SQL calls
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_parsed": 100}
        ]

        result = load_jaffle_shop_data(mock_session)

        assert isinstance(result, dict)
        expected_tables = {
            "raw_customers",
            "raw_orders",
            "raw_order_items",
            "raw_products",
            "raw_stores",
            "raw_supplies",
        }
        assert set(result.keys()) == expected_tables

    def test_executes_begin_and_commit_on_success(
        self, mock_session: MagicMock
    ) -> None:
        """Verify transaction BEGIN and COMMIT are called on successful load."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_parsed": 100}
        ]

        _ = load_jaffle_shop_data(mock_session)

        sql_calls = [c[0][0] for c in mock_session.sql.call_args_list]
        assert "BEGIN" in sql_calls
        assert "COMMIT" in sql_calls

    def test_executes_rollback_on_exception(self, mock_session: MagicMock) -> None:
        """Verify ROLLBACK is called when an exception occurs during loading."""
        # First call (BEGIN) succeeds, subsequent calls fail
        mock_session.sql.return_value.collect.side_effect = [
            [],  # BEGIN
            Exception("Database error"),  # Schema creation fails
        ]

        with pytest.raises(DataIngestionError):
            _ = load_jaffle_shop_data(mock_session)

        sql_calls = [c[0][0] for c in mock_session.sql.call_args_list]
        assert "ROLLBACK" in sql_calls

    def test_wraps_exception_in_data_ingestion_error(
        self, mock_session: MagicMock
    ) -> None:
        """Verify exceptions are wrapped in DataIngestionError with context."""
        mock_session.sql.return_value.collect.side_effect = [
            [],  # BEGIN
            Exception("Connection lost"),
        ]

        with pytest.raises(DataIngestionError) as exc_info:
            _ = load_jaffle_shop_data(mock_session)

        assert "Connection lost" in str(exc_info.value)
        assert "Failed to load Jaffle Shop data" in str(exc_info.value)


class TestLoadSingleTable:
    """Tests for individual table loading logic."""

    def test_raises_error_when_row_count_is_zero(self, mock_session: MagicMock) -> None:
        """Verify DataIngestionError raised when loaded table has 0 rows."""
        # Mock: CREATE succeeds, COPY succeeds, COUNT returns 0
        mock_session.sql.return_value.collect.side_effect = [
            [],  # CREATE TABLE
            [{"rows_parsed": 0}],  # COPY INTO
            [{"COUNT": 0}],  # SELECT COUNT(*)
        ]

        with pytest.raises(DataIngestionError) as exc_info:
            _ = load_single_table(mock_session, "test_table", "(id TEXT)")

        assert "test_table" in str(exc_info.value)
        assert "0 rows" in str(exc_info.value)

    def test_returns_row_count_on_success(self, mock_session: MagicMock) -> None:
        """Verify function returns row count when loading succeeds."""
        mock_session.sql.return_value.collect.side_effect = [
            [],  # CREATE TABLE
            [{"rows_parsed": 500}],  # COPY INTO
            [{"COUNT": 500}],  # SELECT COUNT(*)
        ]

        result = load_single_table(mock_session, "test_table", "(id TEXT)")

        assert result == 500


class TestRollbackTransaction:
    """Tests for transaction rollback behavior."""

    def test_executes_rollback_sql(self, mock_session: MagicMock) -> None:
        """Verify ROLLBACK SQL is executed."""
        rollback_transaction(mock_session)

        mock_session.sql.assert_called_with("ROLLBACK")

    def test_suppresses_rollback_exceptions(self, mock_session: MagicMock) -> None:
        """Verify exceptions during rollback are suppressed (logged only)."""
        mock_session.sql.return_value.collect.side_effect = Exception("Rollback failed")

        # Should not raise
        rollback_transaction(mock_session)
