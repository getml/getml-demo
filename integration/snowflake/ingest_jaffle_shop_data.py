"""Ingest Jaffle Shop data into Snowflake for getML Feature Store integration.

Loads raw Jaffle Shop dataset (Parquet files) from a public GCS bucket into the
RAW schema in Snowflake. Infrastructure (warehouse, database) is auto-created
if missing.

Prerequisites:
    - Snowflake account with appropriate privileges
    - SNOWFLAKE_* environment variables set for authentication and configuration

Usage:
    uv run python ingest_jaffle_shop_data.py
"""

import logging
import sys

from data import (
    SnowflakeSettings,
    create_session,
    ingestion,
)

logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
    """Ingest Jaffle Shop raw data into Snowflake.

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


if __name__ == "__main__":
    main()
