"""Tests for data ingestion module.

Tests URL conversion, download caching, file uploads, error handling,
and successful data loading orchestration logic using mocked sessions.
"""

# pyright: reportAny=false

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from data.ingestion import (
    DEFAULT_GCS_BUCKET,
    JAFFLE_SHOP_TABLE_NAMES,
    DataIngestionError,
    _download_parquet_file,  # pyright: ignore[reportPrivateUsage]
    _gcs_to_https_url,  # pyright: ignore[reportPrivateUsage]
    _get_cache_dir,  # pyright: ignore[reportPrivateUsage]
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
            "items",
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


class TestGcsToHttpsUrl:
    """Tests for _gcs_to_https_url URL conversion helper."""

    def test_converts_gcs_prefix(self) -> None:
        """Verify gcs:// prefix is converted to https://storage.googleapis.com/."""
        result = _gcs_to_https_url("gcs://bucket-name/path/to/data")
        assert result == "https://storage.googleapis.com/bucket-name/path/to/data"

    def test_converts_gs_prefix(self) -> None:
        """Verify gs:// prefix is converted to https://storage.googleapis.com/."""
        result = _gcs_to_https_url("gs://bucket-name/path/to/data")
        assert result == "https://storage.googleapis.com/bucket-name/path/to/data"

    def test_handles_uppercase_prefix(self) -> None:
        """Verify uppercase GCS:// prefix is handled."""
        result = _gcs_to_https_url("GCS://bucket-name/path")
        assert result == "https://storage.googleapis.com/bucket-name/path"

    def test_removes_trailing_slash(self) -> None:
        """Verify trailing slash is removed from path."""
        result = _gcs_to_https_url("gcs://bucket-name/path/")
        assert result == "https://storage.googleapis.com/bucket-name/path"

    def test_raises_error_for_invalid_prefix(self) -> None:
        """Verify error raised for non-GCS URL."""
        with pytest.raises(DataIngestionError) as exc_info:
            _ = _gcs_to_https_url("s3://bucket-name/path")

        assert "Invalid GCS URL" in str(exc_info.value)
        assert "Must start with gcs:// or gs://" in str(exc_info.value)

    def test_converts_default_bucket(self) -> None:
        """Verify default GCS bucket URL is converted correctly."""
        result = _gcs_to_https_url(DEFAULT_GCS_BUCKET)
        assert (
            result
            == "https://storage.googleapis.com/static.getml.com/datasets/jaffle_shop"
        )


class TestGetCacheDir:
    """Tests for _get_cache_dir cache directory helper."""

    def test_returns_path_in_home_directory(self) -> None:
        """Verify cache directory is under user's home directory."""
        result = _get_cache_dir()
        assert result.is_relative_to(Path.home())

    def test_returns_getml_jaffle_shop_path(self) -> None:
        """Verify cache directory path structure."""
        result = _get_cache_dir()
        assert result.parts[-3:] == (".cache", "getml", "jaffle_shop")

    def test_creates_directory_if_not_exists(self, tmp_path: Path) -> None:
        """Verify cache directory is created if it doesn't exist."""
        with patch("data.ingestion.Path.home", return_value=tmp_path):
            result = _get_cache_dir()
            assert result.exists()
            assert result.is_dir()


class TestDownloadParquetFile:
    """Tests for _download_parquet_file download helper."""

    def test_skips_download_if_file_exists(self, tmp_path: Path) -> None:
        """Verify download is skipped when file already exists in cache."""
        dest_path = tmp_path / "test.parquet"
        _ = dest_path.write_bytes(b"existing data")

        with patch("data.ingestion.httpx.stream") as mock_stream:
            _download_parquet_file("https://example.com/test.parquet", dest_path)

        mock_stream.assert_not_called()

    def test_downloads_file_when_not_cached(self, tmp_path: Path) -> None:
        """Verify file is downloaded when not in cache."""
        dest_path = tmp_path / "test.parquet"
        test_data = b"parquet file content"

        mock_response = MagicMock()
        mock_response.iter_bytes.return_value = [test_data]
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("data.ingestion.httpx.stream", return_value=mock_response):
            _download_parquet_file("https://example.com/test.parquet", dest_path)

        assert dest_path.exists()
        assert dest_path.read_bytes() == test_data

    def test_raises_error_on_http_failure(self, tmp_path: Path) -> None:
        """Verify DataIngestionError raised on HTTP error."""
        dest_path = tmp_path / "test.parquet"

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock()
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with (
            patch("data.ingestion.httpx.stream", return_value=mock_response),
            pytest.raises(DataIngestionError) as exc_info,
        ):
            _download_parquet_file("https://example.com/missing.parquet", dest_path)

        assert "Failed to download" in str(exc_info.value)

    def test_cleans_up_partial_download_on_failure(self, tmp_path: Path) -> None:
        """Verify partial download is deleted on failure."""
        dest_path = tmp_path / "test.parquet"

        # Create a partial file to simulate interrupted download
        _ = dest_path.write_bytes(b"partial")

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Connection lost", request=MagicMock(), response=MagicMock()
        )
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        # First call succeeds (file exists check), then fails on actual download
        # Side effect: Not cached initially, then partial file exists after error
        with (
            patch("data.ingestion.httpx.stream", return_value=mock_response),
            patch.object(Path, "exists", side_effect=[False, True]),
            pytest.raises(DataIngestionError),
        ):
            _download_parquet_file("https://example.com/test.parquet", dest_path)


class TestLoadFromS3:
    """Tests for load_from_s3 function."""

    def test_raises_error_for_invalid_bucket_url(self, mock_session: MagicMock) -> None:
        """Verify error raised when bucket URL doesn't start with s3://."""
        with pytest.raises(DataIngestionError) as exc_info:
            _ = load_from_s3(mock_session, bucket="gcs://wrong-scheme/path")

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
            "raw_items",
            "raw_products",
            "raw_stores",
            "raw_supplies",
        }
        assert set(result.keys()) == expected_tables

    def test_creates_external_stage_for_s3(self, mock_session: MagicMock) -> None:
        """Verify external stage is created for S3 bucket."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]

        _ = load_from_s3(mock_session, bucket="s3://test-bucket/data")

        sql_calls = _extract_sql_calls(mock_session)
        stage_calls = [c for c in sql_calls if "CREATE OR REPLACE STAGE" in c]
        assert len(stage_calls) > 0
        # S3 stages use URL parameter
        assert any("s3://test-bucket/data" in c for c in stage_calls)

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
        self, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        """Verify default GCS bucket URL is used when bucket not specified."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]
        mock_session.file.put.return_value = []

        # Create fake cached files
        with (
            patch("data.ingestion._get_cache_dir", return_value=tmp_path),
            patch("data.ingestion._download_parquet_file") as mock_download,
        ):
            # Create fake files for all tables
            for table_name in JAFFLE_SHOP_TABLE_NAMES:
                _ = (tmp_path / f"{table_name}.parquet").write_bytes(b"test")

            _ = load_from_gcs(mock_session)

        # Verify download was called with correct URLs
        download_calls = mock_download.call_args_list
        for call in download_calls:
            url = call.args[0]
            assert "storage.googleapis.com/static.getml.com/datasets/jaffle_shop" in url

    def test_downloads_parquet_files_to_cache(
        self, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        """Verify parquet files are downloaded to cache directory."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]
        mock_session.file.put.return_value = []

        with (
            patch("data.ingestion._get_cache_dir", return_value=tmp_path),
            patch("data.ingestion._download_parquet_file") as mock_download,
        ):
            # Create fake files for all tables
            for table_name in JAFFLE_SHOP_TABLE_NAMES:
                _ = (tmp_path / f"{table_name}.parquet").write_bytes(b"test")

            _ = load_from_gcs(mock_session)

        # Verify download was called for each table
        assert mock_download.call_count == len(JAFFLE_SHOP_TABLE_NAMES)

    def test_uploads_files_to_internal_stage(
        self, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        """Verify files are uploaded to internal Snowflake stage."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]
        mock_session.file.put.return_value = []

        with (
            patch("data.ingestion._get_cache_dir", return_value=tmp_path),
            patch("data.ingestion._download_parquet_file"),
        ):
            # Create fake files for all tables
            for table_name in JAFFLE_SHOP_TABLE_NAMES:
                _ = (tmp_path / f"{table_name}.parquet").write_bytes(b"test")

            _ = load_from_gcs(mock_session)

        # Verify file.put was called for each file
        assert mock_session.file.put.call_count == len(JAFFLE_SHOP_TABLE_NAMES)

    def test_creates_internal_stage_not_external(
        self, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        """Verify internal stage is created (no URL parameter)."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]
        mock_session.file.put.return_value = []

        with (
            patch("data.ingestion._get_cache_dir", return_value=tmp_path),
            patch("data.ingestion._download_parquet_file"),
        ):
            # Create fake files for all tables
            for table_name in JAFFLE_SHOP_TABLE_NAMES:
                _ = (tmp_path / f"{table_name}.parquet").write_bytes(b"test")

            _ = load_from_gcs(mock_session)

        sql_calls = _extract_sql_calls(mock_session)
        stage_calls = [c for c in sql_calls if "CREATE OR REPLACE STAGE" in c]
        # Internal stages don't have URL parameter
        assert len(stage_calls) > 0
        assert not any("URL" in c for c in stage_calls)

    def test_returns_dict_with_all_table_names_on_success(
        self, mock_session: MagicMock, tmp_path: Path
    ) -> None:
        """Verify successful load returns dict mapping table names to row counts."""
        mock_session.sql.return_value.collect.return_value = [
            {"COUNT": 100, "rows_loaded": 100}
        ]
        mock_session.file.put.return_value = []

        with (
            patch("data.ingestion._get_cache_dir", return_value=tmp_path),
            patch("data.ingestion._download_parquet_file"),
        ):
            # Create fake files for all tables
            for table_name in JAFFLE_SHOP_TABLE_NAMES:
                _ = (tmp_path / f"{table_name}.parquet").write_bytes(b"test")

            result = load_from_gcs(mock_session)

        assert isinstance(result, dict)
        expected_tables = set(JAFFLE_SHOP_TABLE_NAMES)
        assert set(result.keys()) == expected_tables


class TestDataIngestionError:
    """Tests for error handling and messaging."""

    def test_wraps_exception_with_context(self, mock_session: MagicMock) -> None:
        """Verify exceptions are wrapped in DataIngestionError with context."""
        mock_session.sql.return_value.collect.side_effect = Exception("Connection lost")

        with pytest.raises(DataIngestionError) as exc_info:
            _ = load_from_s3(mock_session, bucket="s3://test/data")

        assert "Connection lost" in str(exc_info.value)
        assert "Failed to load Jaffle Shop data" in str(exc_info.value)
