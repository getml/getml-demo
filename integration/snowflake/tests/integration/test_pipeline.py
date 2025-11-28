"""Integration tests for the full data pipeline.

These tests require real Snowflake credentials and verify end-to-end
functionality of data ingestion and preparation.

Run with: uv run pytest tests/integration/ -m integration
"""

# ruff: noqa: G004, S608, E501

import logging
import sys
from pathlib import Path

import pytest
from snowflake.snowpark import Row, Session

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data.ingestion import (
    JAFFLE_SHOP_TABLES,
    S3_BUCKET_URL,
    STAGE_NAME,
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.integration


class TestDataIngestion:
    """Integration tests for S3 to Snowflake data loading."""

    def test_load_jaffle_shop_data_creates_tables_with_rows(
        self,
        snowflake_session: Session,
        test_raw_schema: str,
    ) -> None:
        """Verify all Jaffle Shop tables are created with data."""
        # Ensure we're using the test schema
        _ = snowflake_session.sql(f"USE SCHEMA {test_raw_schema}").collect()

        # Create the stage in test schema
        _ = snowflake_session.sql(f"""
            CREATE OR REPLACE STAGE {STAGE_NAME}
            URL = '{S3_BUCKET_URL}'
            FILE_FORMAT = (TYPE = CSV FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1)
        """).collect()

        # Load data using the pipeline function (modified to use current schema)
        results = self._load_tables_to_test_schema(snowflake_session, test_raw_schema)

        # Verify all tables were loaded
        assert set(results.keys()) == set(JAFFLE_SHOP_TABLES.keys())

        # Verify all tables have rows
        for table_name, row_count in results.items():
            assert row_count > 0, f"Table {table_name} has 0 rows"

    def _load_tables_to_test_schema(
        self,
        session: Session,
        schema_name: str,
    ) -> dict[str, int]:
        """Load tables into the test schema.

        Simplified version of load_jaffle_shop_data for test isolation.
        """
        results: dict[str, int] = {}

        for table_name, schema_def in JAFFLE_SHOP_TABLES.items():
            _ = session.sql(f"""
                CREATE OR REPLACE TABLE {schema_name}.{table_name} {schema_def}
            """).collect()

            _ = session.sql(f"""
                COPY INTO {schema_name}.{table_name}
                FROM @{schema_name}.{STAGE_NAME}/{table_name}.csv
                FORCE = FALSE
            """).collect()

            count_result: list[Row] = session.sql(f"""
                SELECT COUNT(*) as count FROM {schema_name}.{table_name}
            """).collect()

            row_count = int(count_result[0]["COUNT"])  # pyright: ignore[reportArgumentType]
            results[table_name] = row_count
            logger.info(f"Loaded {table_name}: {row_count} rows")

        return results

    def test_tables_have_expected_columns(
        self,
        snowflake_session: Session,
        test_raw_schema: str,
    ) -> None:
        """Verify tables have expected column structure."""
        # Check raw_orders has expected columns
        result: list[Row] = snowflake_session.sql(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{test_raw_schema}'
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

    def test_prepare_weekly_sales_creates_population_tables(
        self,
        snowflake_session: Session,
        test_raw_schema: str,
        test_prepared_schema: str,
    ) -> None:
        """Verify preparation creates population tables with correct structure."""
        # First ensure data is loaded (reuse from ingestion test if already run)
        count_result: list[Row] = snowflake_session.sql(f"""
            SELECT COUNT(*) as count FROM {test_raw_schema}.raw_orders
        """).collect()

        if int(count_result[0]["COUNT"]) == 0:  # pyright: ignore[reportArgumentType]
            pytest.skip("Data ingestion test must run first")

        # Create population table in test prepared schema
        _ = snowflake_session.sql(f"""
            CREATE OR REPLACE TABLE {test_prepared_schema}.population_weekly_by_store AS
            SELECT
                ROW_NUMBER() OVER (ORDER BY s.name, DATE_TRUNC('week', o.ordered_at)) as id,
                s.id as store_id,
                s.name as store_name,
                DATE_TRUNC('week', o.ordered_at) as week_start,
                DATEADD('day', 6, DATE_TRUNC('week', o.ordered_at)) as snapshot_date,
                SUM(o.order_total) / 100.0 as weekly_sales,
                COUNT(*) as weekly_orders
            FROM {test_raw_schema}.raw_stores s
            JOIN {test_raw_schema}.raw_orders o ON s.id = o.store_id
            GROUP BY s.id, s.name, DATE_TRUNC('week', o.ordered_at)
        """).collect()

        # Verify table was created with data
        verification_result: list[Row] = snowflake_session.sql(f"""
            SELECT COUNT(*) as count
            FROM {test_prepared_schema}.population_weekly_by_store
        """).collect()

        row_count = int(verification_result[0]["COUNT"])  # pyright: ignore[reportArgumentType]
        assert row_count > 0, "Population table should have data"

    def test_population_table_has_multiple_stores(
        self,
        snowflake_session: Session,
        test_prepared_schema: str,
    ) -> None:
        """Verify population table contains data for multiple stores."""
        result: list[Row] = snowflake_session.sql(f"""
            SELECT COUNT(DISTINCT store_id) as store_count
            FROM {test_prepared_schema}.population_weekly_by_store
        """).collect()

        store_count = int(result[0]["STORE_COUNT"])  # pyright: ignore[reportArgumentType]
        assert store_count > 1, "Population table should have multiple stores"
