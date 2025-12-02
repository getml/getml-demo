#!/usr/bin/env python3
"""
Ingest parquet files from GCS to Databricks Delta Lake.

This is a CLI wrapper around the ingestion module. For programmatic use,
import the module directly:

    from integration.databricks.data import ingestion

Usage:
    1. Authenticate with Databricks CLI: databricks auth login --host <workspace-url>
    2. Run: python ingest_to_databricks.py

Environment variables (optional):
    DATABRICKS_CONFIG_PROFILE: Databricks CLI profile name
"""

from __future__ import annotations

import logging
import sys

from data import ingestion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Main entry point for the ingestion script."""

    logger.info("Starting parquet ingestion to Databricks Delta Lake")

    try:
        loaded = ingestion.load_from_gcs()
        logger.info(f"Completed: {len(loaded)} tables ingested")
        return 0 if len(loaded) == len(ingestion.JAFFLE_SHOP_TABLES) else 1
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
