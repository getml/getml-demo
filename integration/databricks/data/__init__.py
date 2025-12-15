"""Databricks data ingestion and preparation for getML.

This module provides utilities for loading data from GCS into Databricks
and preparing weekly sales forecasting datasets.
"""

from integration.databricks.data import ingestion, preparation
from integration.databricks.data.preparation import (
    DEFAULT_POPULATION_TABLE_NAME,
    DataPreparationError,
    create_weekly_sales_by_store_with_target,
)

__all__ = [
    "DEFAULT_POPULATION_TABLE_NAME",
    "DataPreparationError",
    "create_weekly_sales_by_store_with_target",
    "ingestion",
    "preparation",
]
