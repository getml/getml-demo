-- Create external stage pointing to a GCS bucket for Parquet data ingestion
-- Requires a storage integration for authentication
CREATE OR REPLACE STAGE {schema_name}.{stage_name}
    URL = '{bucket_url}'
    STORAGE_INTEGRATION = {storage_integration}
    FILE_FORMAT = {schema_name}.PARQUET_FORMAT
