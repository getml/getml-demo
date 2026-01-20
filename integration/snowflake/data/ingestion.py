"""Data ingestion from cloud storage to Snowflake for the Jaffle Shop dataset.

This module loads Parquet data from GCS or S3 buckets into Snowflake.

For GCS:
- Downloads files via HTTPS to a local cache (~/.cache/getml/jaffle_shop/)
- Uploads to an internal Snowflake stage using session.file.put()
- No GCP credentials or storage integration required

For S3:
- Uses external staging with COPY INTO commands
- Public S3 buckets work without credentials

When settings are provided, the module auto-bootstraps required infrastructure
(warehouse and database) if they don't exist.

Usage example:
    from data import (
        SnowflakeSettings,
        create_session,
        load_from_gcs,
    )

    settings = SnowflakeSettings.from_env()
    with create_session(settings) as session:
        # Load from GCS - auto-bootstraps warehouse + database
        results = load_from_gcs(session, settings=settings)
"""

from __future__ import annotations

# ruff: noqa: G004, S608
import logging
from pathlib import Path

import httpx
from snowflake.snowpark import Row, Session

from ._bootstrap import ensure_infrastructure
from ._settings import SnowflakeSettings
from ._sql_loader import load_sql

logger: logging.Logger = logging.getLogger(__name__)

JAFFLE_SHOP_TABLE_NAMES: list[str] = [
    "raw_customers",
    "raw_orders",
    "raw_items",
    "raw_products",
    "raw_stores",
    "raw_supplies",
]

DEFAULT_GCS_BUCKET = "gcs://static.getml.com/datasets/jaffle_shop"
DEFAULT_STAGE_NAME = "JAFFLE_SHOP_STAGE"


class DataIngestionError(Exception):
    """Raised when data ingestion fails."""


# =============================================================================
# Public API
# =============================================================================


def load_from_gcs(
    session: Session,
    settings: SnowflakeSettings | None = None,
    bucket: str = DEFAULT_GCS_BUCKET,
    destination_schema: str = "RAW",
) -> dict[str, int]:
    """Load Jaffle Shop data from GCS bucket into Snowflake.

    Downloads parquet files via HTTPS to a local cache, uploads them to an
    internal Snowflake stage, then loads into tables using COPY INTO.

    No GCP credentials or storage integration required - files are fetched
    via public HTTPS URLs.

    When settings are provided, auto-bootstraps the warehouse and database
    if they don't exist.

    Args:
        session: Active Snowflake Snowpark session.
        settings: Optional settings for auto-bootstrapping warehouse and database.
            When provided, ensures infrastructure exists before loading data.
        bucket: GCS bucket URL (gcs:// or gs:// prefix).
        destination_schema: Target schema name for loaded tables.

    Returns:
        Dictionary mapping table names to row counts.

    Raises:
        DataIngestionError: If data loading fails.
        BootstrapError: If auto-bootstrap fails due to insufficient privileges.
    """
    if settings is not None:
        ensure_infrastructure(session, settings)
        if settings.warehouse:
            session.use_warehouse(settings.warehouse)
        if settings.database:
            session.use_database(settings.database)

    try:
        https_base_url: str = _gcs_to_https_url(gcs_url=bucket)
        cache_dir: Path = _get_cache_dir()
        local_files: dict[str, Path] = {}

        for table_name in JAFFLE_SHOP_TABLE_NAMES:
            file_name: str = f"{table_name}.parquet"
            url: str = f"{https_base_url}/{file_name}"
            local_path: Path = cache_dir / file_name
            _download_parquet_file(url, dest_path=local_path)
            local_files[table_name] = local_path

        _create_schema(session, schema_name=destination_schema)
        _create_parquet_file_format(session, schema_name=destination_schema)
        _create_internal_stage(
            session,
            schema_name=destination_schema,
            stage_name=DEFAULT_STAGE_NAME,
        )

        _upload_files_to_stage(
            session,
            local_files,
            schema_name=destination_schema,
            stage_name=DEFAULT_STAGE_NAME,
        )

        results: dict[str, int] = _load_all_tables(
            session,
            schema_name=destination_schema,
        )

    except Exception as e:
        raise DataIngestionError(
            f"Failed to load Jaffle Shop data into Snowflake. Error: {e}"
        ) from e

    _log_completion_summary(results, schema_name=destination_schema)
    return results


def load_from_s3(
    session: Session,
    bucket: str,
    settings: SnowflakeSettings | None = None,
    destination_schema: str = "RAW",
) -> dict[str, int]:
    """Load Jaffle Shop data from public S3 bucket into Snowflake.

    Creates the destination schema if needed, sets up a Parquet file format
    and external stage pointing to the S3 bucket, then loads all tables
    using COPY INTO with schema inference.

    When settings are provided, auto-bootstraps the warehouse and database
    if they don't exist.

    Args:
        session: Active Snowflake Snowpark session.
        bucket: S3 bucket URL (s3:// prefix). Must be publicly accessible.
        settings: Optional settings for auto-bootstrapping warehouse and database.
            When provided, ensures infrastructure exists before loading data.
        destination_schema: Target schema name for loaded tables.

    Returns:
        Dictionary mapping table names to row counts.

    Raises:
        DataIngestionError: If data loading fails.
        BootstrapError: If auto-bootstrap fails due to insufficient privileges.
    """
    if not bucket.lower().startswith("s3://"):
        raise DataIngestionError(
            f"Invalid S3 bucket URL: {bucket}. Must start with s3://"
        )

    if settings is not None:
        ensure_infrastructure(session, settings)
        if settings.warehouse:
            session.use_warehouse(settings.warehouse)
        if settings.database:
            session.use_database(settings.database)

    try:
        _create_schema(session, schema_name=destination_schema)
        _create_parquet_file_format(session, schema_name=destination_schema)
        _create_external_stage_s3(
            session,
            bucket_url=bucket,
            schema_name=destination_schema,
        )
        results: dict[str, int] = _load_all_tables(
            session,
            schema_name=destination_schema,
        )
    except Exception as e:
        raise DataIngestionError(
            f"Failed to load Jaffle Shop data into Snowflake. Error: {e}"
        ) from e

    _log_completion_summary(results, schema_name=destination_schema)
    return results


# =============================================================================
# GCS Download Helpers
# =============================================================================


def _gcs_to_https_url(gcs_url: str) -> str:
    """Convert GCS URL to HTTPS URL for public access.

    Args:
        gcs_url: GCS bucket URL with gcs:// or gs:// prefix.

    Returns:
        HTTPS URL for the same resource.

    Examples:
        gcs://static.getml.com/datasets/jaffle_shop
        -> https://storage.googleapis.com/static.getml.com/datasets/jaffle_shop
    """
    if gcs_url.lower().startswith("gcs://"):
        path = gcs_url[6:]
    elif gcs_url.lower().startswith("gs://"):
        path = gcs_url[5:]
    else:
        raise DataIngestionError(
            f"Invalid GCS URL: {gcs_url}. Must start with gcs:// or gs://"
        )

    path: str = path.rstrip("/")

    return f"https://storage.googleapis.com/{path}"


def _get_cache_dir() -> Path:
    """Get persistent cache directory for downloaded parquet files.

    Creates the directory if it doesn't exist.

    Returns:
        Path to cache directory (~/.cache/getml/jaffle_shop/).
    """
    cache_dir = Path.home() / ".cache" / "getml" / "jaffle_shop"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _download_parquet_file(url: str, dest_path: Path) -> None:
    """Download a parquet file from URL to local path.

    Skips download if file already exists in cache.

    Args:
        url: HTTPS URL to download from.
        dest_path: Local path to save the file.

    Raises:
        DataIngestionError: If download fails.
    """
    if dest_path.exists():
        logger.info(f"Using cached file: {dest_path.name}")
        return

    logger.info(f"Downloading {dest_path.name}...")

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
            _ = response.raise_for_status()
            with dest_path.open("wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    _ = f.write(chunk)
    except httpx.HTTPError as e:
        # Clean up partial download
        if dest_path.exists():
            dest_path.unlink()
        raise DataIngestionError(f"Failed to download {url}: {e}") from e

    logger.info(f"  ✓ Downloaded {dest_path.name}")


def _upload_files_to_stage(
    session: Session,
    local_files: dict[str, Path],
    schema_name: str,
    stage_name: str,
) -> None:
    """Upload local parquet files to internal Snowflake stage.

    Args:
        session: Active Snowflake Snowpark session.
        local_files: Dictionary mapping table names to local file paths.
        schema_name: Schema where the stage is located.
        stage_name: Name of the internal stage.
    """
    logger.info(f"Uploading files to stage @{schema_name}.{stage_name}...")

    for local_path in local_files.values():
        logger.info(f"  Uploading {local_path.name}...")
        put_result = session.file.put(
            local_file_name=str(local_path),
            stage_location=f"@{schema_name}.{stage_name}/",
            auto_compress=False,
            overwrite=True,
        )
        if put_result:
            for row in put_result:
                status: str = row.status if hasattr(row, "status") else "UPLOADED"
                logger.info(f"    ✓ {local_path.name}: {status}")


# =============================================================================
# Schema and Stage Creation
# =============================================================================


def _create_schema(session: Session, schema_name: str) -> None:
    """Create schema if it doesn't exist."""
    logger.info(f"Creating {schema_name} schema...")
    sql: str = load_sql(path="common/create_schema.sql", schema_name=schema_name)
    _ = session.sql(sql).collect()
    logger.info(f"✓ {schema_name} schema ready")


def _create_parquet_file_format(session: Session, schema_name: str) -> None:
    """Create Parquet file format for data ingestion."""
    logger.info("Creating Parquet file format...")
    sql: str = load_sql(
        path="ingestion/create_parquet_file_format.sql",
        schema_name=schema_name,
    )
    _ = session.sql(sql).collect()
    logger.info("✓ Parquet file format ready")


def _create_internal_stage(
    session: Session,
    schema_name: str,
    stage_name: str,
) -> None:
    """Create internal stage for uploaded files."""
    logger.info(f"Creating internal stage {stage_name}...")
    sql: str = load_sql(
        path="ingestion/create_internal_stage.sql",
        stage_name=stage_name,
        schema_name=schema_name,
    )
    _ = session.sql(sql).collect()
    logger.info(f"✓ Internal stage {stage_name} created")


def _create_external_stage_s3(
    session: Session,
    bucket_url: str,
    schema_name: str,
) -> None:
    """Create external stage pointing to public S3 bucket."""
    logger.info(f"Creating external stage {DEFAULT_STAGE_NAME}...")
    sql: str = load_sql(
        path="ingestion/create_stage_s3_public.sql",
        stage_name=DEFAULT_STAGE_NAME,
        bucket_url=bucket_url,
        schema_name=schema_name,
    )
    _ = session.sql(sql).collect()
    logger.info(f"✓ External stage {DEFAULT_STAGE_NAME} created")


# =============================================================================
# Table Loading
# =============================================================================


def _load_all_tables(session: Session, schema_name: str) -> dict[str, int]:
    """Load all Jaffle Shop tables from stage."""
    logger.info("Loading tables from stage...")
    results: dict[str, int] = {}

    for source_name in JAFFLE_SHOP_TABLE_NAMES:
        table_name = source_name.removeprefix("raw_")
        row_count: int = _load_single_table(
            session, source_name, table_name, schema_name
        )
        results[table_name] = row_count

    return results


def _load_single_table(
    session: Session,
    source_name: str,
    table_name: str,
    schema_name: str,
) -> int:
    """Load a single table from stage.

    Uses a two-step process:
    1. Creates empty table with schema inferred from Parquet metadata (INFER_SCHEMA)
    2. Copies data from stage using MATCH_BY_COLUMN_NAME for proper column mapping
    """
    logger.info(f"Loading {source_name} -> {table_name}...")

    create_sql: str = load_sql(
        path="ingestion/create_table_from_parquet.sql",
        source_name=source_name,
        table_name=table_name,
        stage_name=DEFAULT_STAGE_NAME,
        schema_name=schema_name,
    )
    _ = session.sql(create_sql).collect()

    copy_sql: str = load_sql(
        path="ingestion/copy_into_table.sql",
        source_name=source_name,
        table_name=table_name,
        stage_name=DEFAULT_STAGE_NAME,
        schema_name=schema_name,
    )
    _ = session.sql(query=copy_sql).collect()

    count_sql = f"SELECT COUNT(*) as count FROM {schema_name}.{table_name}"
    count_result: list[Row] = session.sql(count_sql).collect()

    row_count = int(count_result[0]["COUNT"])  # pyright: ignore[reportArgumentType]
    logger.info(f"  ✓ {row_count:,} rows loaded")

    if row_count == 0:
        raise DataIngestionError(f"Table {table_name} has 0 rows after loading")

    return row_count


def _log_completion_summary(results: dict[str, int], schema_name: str) -> None:
    """Log summary of loaded tables."""
    table_lines = "\n".join(
        f"  • {name}: {count:,} rows" for name, count in results.items()
    )
    logger.info(f"""
================================================================================
DATA LOADING COMPLETE!
================================================================================
Successfully loaded {len(results)} tables into {schema_name} schema:
{table_lines}
""")
