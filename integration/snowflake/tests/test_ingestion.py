"""Tests for data ingestion module.

Tests error handling, rollback behavior, storage integration auto-creation,
and successful data loading orchestration logic using mocked Snowflake sessions.
"""

# pyright: reportAny=false

from unittest.mock import MagicMock

import pytest

from data.ingestion import (
    DEFAULT_GCS_BUCKET,
    JAFFLE_SHOP_TABLE_NAMES,
    DataIngestionError,
    get_table_names,
    load_from_gcs,
    load_from_s3,
)


def _extract_sql_calls(mock_session: MagicMock) -> list[str]:
    """Extract SQL strings from mock session.sql() calls.

    Handles both positional and keyword argument styles:
    - session.sql("SELECT ...")
    - session.sql(query="SELECT ...")
    """
    calls: list[str] = []
    for call in mock_session.sql.call_args_list:
        if call.args:
            calls.append(call.args[0])
        elif "query" in call.kwargs:
            calls.append(call.kwargs["query"])
    return calls


class TestGetTableNames:
    """Tests for get_table_names helper function."""

    def test_returns_dict_with_all_jaffle_shop_tables(self) -> None:
        """Verify get_table_names returns all expected table names."""
        result = get_table_names()

        assert isinstance(result, dict)
        assert len(result) == len(JAFFLE_SHOP_TABLE_NAMES)
        expected_keys = {
            "customers",
            "orders",
            "order_items",
            "products",
            "stores",
            "supplies",
        }
        assert set(result.keys()) == expected_keys

    def test_uses_default_raw_schema(self) -> None:
        """Verify default RAW schema is used when not specified."""
        result = get_table_names()

        assert all(name.startswith("RAW.") for name in result.values())
        assert result["orders"] == "RAW.raw_orders"

    def test_uses_custom_schema(self) -> None:
        """Verify custom schema is used when specified."""
        result = get_table_names(schema="CUSTOM")

        assert all(name.startswith("CUSTOM.") for name in result.values())
        assert result["orders"] == "CUSTOM.raw_orders"

    def test_preserves_raw_prefix_in_table_name(self) -> None:
        """Verify the raw_ prefix is preserved in the qualified table name."""
        result = get_table_names("MY_SCHEMA")

        assert result["customers"] == "MY_SCHEMA.raw_customers"
        assert result["stores"] == "MY_SCHEMA.raw_stores"


class TestLoadFromS3:
    """Tests for load_from_s3 function."""

    def test_raises_error_for_invalid_bucket_url(self, mock_session: MagicMock) -> None:
        """Verify error raised when bucket URL doesn't start with s3://."""
        with pytest.raises(DataIngestionError) as exc_info:
            load_from_s3(mock_session, bucket="gcs://wrong-scheme/path")

        assert "Invalid S3 bucket URL" in str(exc_info.value)
        assert "Must start with s3://" in str(exc_info.value)

    def test_returns_dict_with_all_table_names_on_success(
        self, mock_session: MagicMock
    ) -> None:
        """Verify successful load returns dict mapping table names to row counts."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]

        result = load_from_s3(
            mock_session,
            bucket="s3://test-bucket/jaffle-shop",
        )

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
            {"COUNT": 100, "rows_loaded": 100}
        ]

        _ = load_from_s3(mock_session, bucket="s3://test-bucket/data")

        sql_calls = _extract_sql_calls(mock_session)
        assert "BEGIN" in sql_calls
        assert "COMMIT" in sql_calls

    def test_executes_rollback_on_exception(self, mock_session: MagicMock) -> None:
        """Verify ROLLBACK is called when an exception occurs during loading."""
        mock_session.sql.return_value.collect.side_effect = [
            [],  # BEGIN
            Exception("Database error"),  # Schema creation fails
        ]

        with pytest.raises(DataIngestionError):
            _ = load_from_s3(mock_session, bucket="s3://test-bucket/data")

        sql_calls = _extract_sql_calls(mock_session)
        assert "ROLLBACK" in sql_calls

    def test_uses_custom_destination_schema(self, mock_session: MagicMock) -> None:
        """Verify custom destination schema is used in SQL calls."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]

        _ = load_from_s3(
            mock_session,
            bucket="s3://test-bucket/data",
            destination_schema="CUSTOM_SCHEMA",
        )

        sql_calls = _extract_sql_calls(mock_session)
        schema_creation_calls = [c for c in sql_calls if "CREATE SCHEMA" in c]
        assert any("CUSTOM_SCHEMA" in c for c in schema_creation_calls)


class TestLoadFromGcs:
    """Tests for load_from_gcs function."""

    def test_uses_default_gcs_bucket_when_not_specified(
        self, mock_session: MagicMock
    ) -> None:
        """Verify default GCS bucket URL is used when bucket not specified."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]

        _ = load_from_gcs(
            mock_session,
            storage_integration="TEST_INTEGRATION",
        )

        sql_calls = _extract_sql_calls(mock_session)
        stage_calls = [c for c in sql_calls if "CREATE OR REPLACE STAGE" in c]
        assert any(DEFAULT_GCS_BUCKET in c for c in stage_calls)

    def test_verifies_storage_integration_exists(self, mock_session: MagicMock) -> None:
        """Verify storage integration is checked before loading."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]

        _ = load_from_gcs(
            mock_session,
            storage_integration="MY_INTEGRATION",
        )

        sql_calls = _extract_sql_calls(mock_session)
        describe_calls = [c for c in sql_calls if "DESCRIBE" in c.upper()]
        assert len(describe_calls) > 0

    def test_raises_error_when_integration_missing_and_no_factory(
        self, mock_session: MagicMock
    ) -> None:
        """Verify error raised when integration missing and no factory provided."""
        mock_session.sql.return_value.collect.side_effect = Exception(
            "Integration not found"
        )

        with pytest.raises(DataIngestionError) as exc_info:
            _ = load_from_gcs(
                mock_session,
                storage_integration="MISSING_INTEGRATION",
            )

        assert "does not exist" in str(exc_info.value)
        assert "integration_factory" in str(exc_info.value)

    def test_attempts_auto_creation_when_factory_provided(
        self, mock_session: MagicMock
    ) -> None:
        """Verify auto-creation is attempted when factory is provided."""
        mock_factory = MagicMock()
        call_count = 0

        def sql_side_effect(
            sql: str | None = None, query: str | None = None
        ) -> MagicMock:
            nonlocal call_count
            sql_str = sql or query or ""
            result = MagicMock()
            if "DESCRIBE" in sql_str.upper():
                call_count += 1
                if call_count == 1:
                    result.collect.side_effect = Exception("Integration not found")
                else:
                    result.collect.return_value = []
            else:
                result.collect.return_value = [{"COUNT": 100, "rows_loaded": 100}]
            return result

        mock_session.sql.side_effect = sql_side_effect

        _ = load_from_gcs(
            mock_session,
            storage_integration="NEW_INTEGRATION",
            integration_factory=mock_factory,
        )

        mock_factory.assert_called_once()

    def test_uses_storage_integration_in_stage_creation(
        self, mock_session: MagicMock
    ) -> None:
        """Verify storage integration is included in stage creation SQL."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]

        _ = load_from_gcs(
            mock_session,
            storage_integration="MY_GCS_INTEGRATION",
        )

        sql_calls = _extract_sql_calls(mock_session)
        stage_calls = [c for c in sql_calls if "STORAGE_INTEGRATION" in c]
        assert len(stage_calls) > 0
        assert any("MY_GCS_INTEGRATION" in c for c in stage_calls)


class TestDataIngestionError:
    """Tests for error handling and messaging."""

    def test_wraps_exception_with_context(self, mock_session: MagicMock) -> None:
        """Verify exceptions are wrapped in DataIngestionError with context."""
        mock_session.sql.return_value.collect.side_effect = [
            [],  # BEGIN
            Exception("Connection lost"),
        ]

        with pytest.raises(DataIngestionError) as exc_info:
            _ = load_from_s3(mock_session, bucket="s3://test/data")

        assert "Connection lost" in str(exc_info.value)
        assert "Failed to load Jaffle Shop data" in str(exc_info.value)
