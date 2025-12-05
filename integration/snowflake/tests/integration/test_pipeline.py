"""Integration tests for the full data pipeline.

These tests require real Snowflake credentials and verify end-to-end
functionality of data ingestion and preparation.

Run with: uv run pytest tests/integration/ -m integration

Required environment variables:
- SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD, etc.
- GCS_STORAGE_INTEGRATION: Name of the storage integration for GCS access
"""

import logging

import pytest
from snowflake.snowpark import Row, Session

from data.ingestion import JAFFLE_SHOP_TABLE_NAMES

from .conftest import StorageConfig, load_jaffle_shop_data

logger = logging.getLogger(__name__)

pytestmark: pytest.MarkDecorator = pytest.mark.integration


class TestDataIngestion:
    """Integration tests for cloud storage to Snowflake data loading."""

    @pytest.mark.dependency(name="data_ingestion")
    def test_load_jaffle_shop_data_creates_tables_with_rows(
        self,
        snowflake_session: Session,
        storage_config: StorageConfig,
    ) -> None:
        """Verify all Jaffle Shop tables are created with data."""
        results = load_jaffle_shop_data(snowflake_session, storage_config)

        # Verify all tables were loaded
        assert set(results.keys()) == set(JAFFLE_SHOP_TABLE_NAMES)

        # Verify all tables have rows
        for table_name, row_count in results.items():
            assert row_count > 0, f"Table {table_name} has 0 rows"

    @pytest.mark.dependency(depends=["data_ingestion"])
    def test_tables_have_expected_columns(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify tables have expected column structure."""
        result: list[Row] = snowflake_session.sql("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'RAW'
            AND TABLE_NAME = 'RAW_ORDERS'
            ORDER BY ORDINAL_POSITION
        """).collect()

        column_names = [str(row["COLUMN_NAME"]) for row in result]  # pyright: ignore[reportUnknownArgumentType]

        # Column names are inferred from Parquet, check key columns exist
        expected_columns = [
            "ID",
            "CUSTOMER",
            "ORDERED_AT",
            "STORE_ID",
            "SUBTOTAL",
            "TAX_PAID",
            "ORDER_TOTAL",
        ]
        for col in expected_columns:
            assert col in column_names, f"Expected column {col} not found"
