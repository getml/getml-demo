#!/usr/bin/env python3
"""Prepare Jaffle Shop data in Snowflake for getML Feature Store integration.

Loads raw data from GCS and creates the weekly sales forecasting population table.
Infrastructure (warehouse, database) is auto-created if missing.

Prerequisites:
    - Snowflake account with appropriate privileges
    - SNOWFLAKE_* environment variables set for authentication and configuration

Usage:
    uv run python prepare_jaffle_shop_data_for_snowflake.py
"""

import logging
import sys

from data import (
    SnowflakeSettings,
    create_session,
    ingestion,
    preparation,
)

logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
    """Load and prepare Jaffle Shop data for getML.

    Note:
        Set basicConfig.level to logging.DEBUG for more verbose output.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    settings = SnowflakeSettings.from_env()

    with create_session(settings) as session:
        _ = ingestion.load_from_gcs(
            session,
            settings=settings,
            bucket="gcs://static.getml.com/datasets/jaffle_shop",
            destination_schema="RAW",
        )

        _ = preparation.create_weekly_sales_by_store_with_target(
            session,
            settings=settings,
            source_schema="RAW",
            target_schema="PREPARED",
            table_name="WEEKLY_SALES_BY_STORE_WITH_TARGET",
        )


if __name__ == "__main__":
    main()
