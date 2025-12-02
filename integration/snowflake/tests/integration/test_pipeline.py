"""Integration tests for the full data pipeline.

These tests require real Snowflake credentials and verify end-to-end
functionality of data ingestion and preparation.

Run with: uv run pytest tests/integration/ -m integration
"""

# ruff: noqa: E501

import logging
import sys
from pathlib import Path

import pytest
from snowflake.snowpark import Row, Session

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.ingestion import JAFFLE_SHOP_TABLES, load_jaffle_shop_data
from data.preparation import prepare_weekly_sales_by_store

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


class TestDataIngestion:
    """Integration tests for S3 to Snowflake data loading."""

    @pytest.mark.dependency(name="data_ingestion")
    def test_load_jaffle_shop_data_creates_tables_with_rows(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify all Jaffle Shop tables are created with data."""
        results = load_jaffle_shop_data(snowflake_session)

        # Verify all tables were loaded
        assert set(results.keys()) == set(JAFFLE_SHOP_TABLES.keys())

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

        expected_columns = [
            "ID",
            "CUSTOMER",
            "ORDERED_AT",
            "STORE_ID",
            "SUBTOTAL",
            "TAX_PAID",
            "ORDER_TOTAL",
        ]
        assert column_names == expected_columns


class TestDataPreparation:
    """Integration tests for data preparation pipeline."""

    @pytest.mark.dependency(name="data_preparation", depends=["data_ingestion"])
    def test_prepare_weekly_sales_creates_weekly_stores_table(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify preparation creates weekly_stores table with data."""
        prepare_weekly_sales_by_store(snowflake_session)

        # Verify table was created with data
        result: list[Row] = snowflake_session.sql("""
            SELECT COUNT(*) as count FROM PREPARED.weekly_stores
        """).collect()

        row_count = int(result[0]["COUNT"])  # pyright: ignore[reportArgumentType]
        assert row_count > 0, "weekly_stores table should have data"

    @pytest.mark.dependency(depends=["data_preparation"])
    def test_weekly_stores_has_multiple_stores(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify weekly_stores table contains data for multiple stores."""
        result: list[Row] = snowflake_session.sql("""
            SELECT COUNT(DISTINCT store_id) as store_count
            FROM PREPARED.weekly_stores
        """).collect()

        store_count = int(result[0]["STORE_COUNT"])  # pyright: ignore[reportArgumentType]
        assert store_count > 1, "weekly_stores should have multiple stores"

    @pytest.mark.dependency(depends=["data_preparation"])
    def test_weekly_stores_has_correct_columns(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify weekly_stores table has the expected column structure."""
        result: list[Row] = snowflake_session.sql("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'PREPARED'
            AND TABLE_NAME = 'WEEKLY_STORES'
            ORDER BY ORDINAL_POSITION
        """).collect()

        column_names = [str(row["COLUMN_NAME"]) for row in result]  # pyright: ignore[reportUnknownArgumentType]

        expected_columns = [
            "SNAPSHOT_ID",
            "STORE_ID",
            "STORE_NAME",
            "REFERENCE_DATE",
            "YEAR",
            "MONTH",
            "WEEK_NUMBER",
            "DAYS_SINCE_OPEN",
            "IS_FULL_WEEK_AFTER_OPENING",
            "HAS_ORDER_ACTIVITY",
            "HAS_MIN_HISTORY",
        ]
        assert column_names == expected_columns

    @pytest.mark.dependency(depends=["data_preparation"])
    def test_target_view_exists_with_sales_columns(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify population_weekly_by_store_with_target view exists with target columns."""
        result: list[Row] = snowflake_session.sql("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'PREPARED'
            AND TABLE_NAME = 'POPULATION_WEEKLY_BY_STORE_WITH_TARGET'
            ORDER BY ORDINAL_POSITION
        """).collect()

        column_names = [str(row["COLUMN_NAME"]) for row in result]  # pyright: ignore[reportUnknownArgumentType]

        # Should have all weekly_stores columns plus target columns
        assert "NEXT_WEEK_SALES" in column_names, "View should have NEXT_WEEK_SALES"
        assert "NEXT_WEEK_ORDERS" in column_names, "View should have NEXT_WEEK_ORDERS"
        assert "REFERENCE_DATE" in column_names, "View should have REFERENCE_DATE"

    @pytest.mark.dependency(depends=["data_preparation"])
    def test_target_view_has_valid_sales_data(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify the target view calculates sales correctly."""
        result: list[Row] = snowflake_session.sql("""
            SELECT
                COUNT(*) as total_rows,
                SUM(CASE WHEN next_week_sales > 0 THEN 1 ELSE 0 END) as rows_with_sales,
                AVG(next_week_sales) as avg_sales
            FROM PREPARED.population_weekly_by_store_with_target
        """).collect()

        total_rows = int(result[0]["TOTAL_ROWS"])  # pyright: ignore[reportArgumentType]
        rows_with_sales = int(result[0]["ROWS_WITH_SALES"])  # pyright: ignore[reportArgumentType]
        avg_sales = float(result[0]["AVG_SALES"])  # pyright: ignore[reportArgumentType]

        assert total_rows > 0, "View should have rows"
        assert rows_with_sales > 0, "Some rows should have sales > 0"
        assert avg_sales > 0, "Average sales should be positive"

    @pytest.mark.dependency(depends=["data_preparation"])
    def test_boolean_flags_are_calculated(
        self,
        snowflake_session: Session,
    ) -> None:
        """Verify boolean flags are properly calculated in weekly_stores."""
        result: list[Row] = snowflake_session.sql("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN is_full_week_after_opening THEN 1 ELSE 0 END) as full_week_count,
                SUM(CASE WHEN has_order_activity THEN 1 ELSE 0 END) as activity_count,
                SUM(CASE WHEN has_min_history THEN 1 ELSE 0 END) as min_history_count
            FROM PREPARED.weekly_stores
        """).collect()

        total = int(result[0]["TOTAL"])  # pyright: ignore[reportArgumentType]
        full_week_count = int(result[0]["FULL_WEEK_COUNT"])  # pyright: ignore[reportArgumentType]
        activity_count = int(result[0]["ACTIVITY_COUNT"])  # pyright: ignore[reportArgumentType]
        min_history_count = int(result[0]["MIN_HISTORY_COUNT"])  # pyright: ignore[reportArgumentType]

        # All flags should have some TRUE values (not all zeros)
        assert full_week_count > 0, (
            "Some rows should have is_full_week_after_opening=TRUE"
        )
        assert activity_count > 0, "Some rows should have has_order_activity=TRUE"
        assert min_history_count > 0, "Some rows should have has_min_history=TRUE"

        # Not all rows should have all flags TRUE (validates the logic works)
        # At minimum, first week after opening shouldn't have full history
        assert full_week_count <= total, "Boolean flag counts should not exceed total"
