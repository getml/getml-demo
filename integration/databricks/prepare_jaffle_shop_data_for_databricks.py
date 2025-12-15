#!/usr/bin/env python3
"""Prepare Jaffle Shop data in Databricks for getML Feature Store integration.

Loads raw data from GCS and creates the weekly sales forecasting population table.
Infrastructure (catalog, schemas) is created as needed.
"""

from __future__ import annotations

import logging

from databricks.connect import DatabricksSession

from .data import ingestion, preparation

logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
    """Load and prepare Jaffle Shop data for getML.

    Note:
        Set basicConfig.level to logging.DEBUG for more verbose output.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )

    logger.info("Starting Jaffle Shop data preparation for Databricks...")

    spark = DatabricksSession.builder.serverless().getOrCreate()

    logger.info("\nStep 1: Loading raw data from GCS...")
    _ = ingestion.load_from_gcs(
        spark=spark,
        bucket="https://static.getml.com/datasets/jaffle_shop/",
        destination_catalog="workspace",
        destination_schema="raw",
    )

    logger.info("\nStep 2: Preparing weekly sales forecasting data...")
    population_table = preparation.create_weekly_sales_by_store_with_target(
        spark,
        source_catalog="workspace",
        source_schema="raw",
        target_catalog="workspace",
        target_schema="prepared",
        table_name="weekly_sales_by_store_with_target",
    )

    logger.info(f"""
================================================================================
✓ DATA PREPARATION COMPLETE
================================================================================

Population table ready for getML: {population_table}

Next steps:
1. Use this table in your getML notebook:
   
   df = spark.table("{population_table}")
   
2. The table contains weekly sales forecasting data with:
   - Store-week combinations as snapshots
   - Target variable: next_week_sales
   - Filtering flags for data quality

For more information, see the getML documentation.
""")


if __name__ == "__main__":
    main()
