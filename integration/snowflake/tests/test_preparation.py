"""Tests for data preparation module.

Tests validation logic and pipeline orchestration using mocked
Snowflake sessions.
"""

# pyright: reportAny=false

from unittest.mock import MagicMock, patch

import pytest

from data.preparation import (
    DEFAULT_POPULATION_TABLE_NAME,
    DataPreparationError,
    _validate_source_tables,
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
            create_weekly_sales_by_store_with_target(mock_session)

    @patch("data.preparation._display_recent_snapshots")
    @patch("data.preparation._perform_data_quality_check")
    @patch("data.preparation._display_overall_statistics")
    @patch("data.preparation._display_store_statistics")
    @patch("data.preparation._display_sample_data")
    @patch("data.preparation._create_target_view")
    @patch("data.preparation._create_weekly_stores_table")
    @patch("data.preparation._analyze_and_display_stores")
    @patch("data.preparation._ensure_target_schema")
    @patch("data.preparation._validate_source_tables")
    def test_uses_default_schemas(  # noqa: PLR0913, PLR0917
        self,
        mock_validate: MagicMock,
        mock_ensure_schema: MagicMock,
        mock_analyze: MagicMock,
        mock_create_table: MagicMock,
        mock_create_view: MagicMock,
        mock_sample: MagicMock,
        mock_store_stats: MagicMock,
        mock_overall_stats: MagicMock,
        mock_quality: MagicMock,
        mock_recent: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Verify default RAW and PREPARED schemas are used."""
        mock_create_table.return_value = []

        result = create_weekly_sales_by_store_with_target(mock_session)

        mock_validate.assert_called_once_with(mock_session, "RAW")
        mock_ensure_schema.assert_called_once_with(mock_session, "PREPARED")
        mock_analyze.assert_called_once_with(mock_session, "RAW")
        mock_create_table.assert_called_once_with(mock_session, "RAW", "PREPARED")
        mock_create_view.assert_called_once_with(
            mock_session, "RAW", "PREPARED", DEFAULT_POPULATION_TABLE_NAME
        )
        assert result == f"PREPARED.{DEFAULT_POPULATION_TABLE_NAME}"

    @patch("data.preparation._display_recent_snapshots")
    @patch("data.preparation._perform_data_quality_check")
    @patch("data.preparation._display_overall_statistics")
    @patch("data.preparation._display_store_statistics")
    @patch("data.preparation._display_sample_data")
    @patch("data.preparation._create_target_view")
    @patch("data.preparation._create_weekly_stores_table")
    @patch("data.preparation._analyze_and_display_stores")
    @patch("data.preparation._ensure_target_schema")
    @patch("data.preparation._validate_source_tables")
    def test_uses_custom_schemas(  # noqa: PLR0913, PLR0917
        self,
        mock_validate: MagicMock,
        mock_ensure_schema: MagicMock,
        mock_analyze: MagicMock,
        mock_create_table: MagicMock,
        mock_create_view: MagicMock,
        mock_sample: MagicMock,
        mock_store_stats: MagicMock,
        mock_overall_stats: MagicMock,
        mock_quality: MagicMock,
        mock_recent: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Verify custom source and target schemas are used when provided."""
        mock_create_table.return_value = []

        result = create_weekly_sales_by_store_with_target(
            mock_session,
            source_schema="MY_RAW",
            target_schema="MY_PREPARED",
            table_name="CUSTOM_TABLE",
        )

        mock_validate.assert_called_once_with(mock_session, "MY_RAW")
        mock_ensure_schema.assert_called_once_with(mock_session, "MY_PREPARED")
        mock_analyze.assert_called_once_with(mock_session, "MY_RAW")
        mock_create_table.assert_called_once_with(mock_session, "MY_RAW", "MY_PREPARED")
        mock_create_view.assert_called_once_with(
            mock_session, "MY_RAW", "MY_PREPARED", "CUSTOM_TABLE"
        )
        assert result == "MY_PREPARED.CUSTOM_TABLE"
