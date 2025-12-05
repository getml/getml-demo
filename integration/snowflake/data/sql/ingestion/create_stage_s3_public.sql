-- Create external stage pointing to a public S3 bucket for Parquet data ingestion
-- No credentials required for public buckets
CREATE OR REPLACE STAGE {schema_name}.{stage_name}
    URL = '{bucket_url}'
    FILE_FORMAT = {schema_name}.PARQUET_FORMAT
