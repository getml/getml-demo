-- Create Parquet file format for data ingestion
-- Uses CREATE OR REPLACE for idempotent execution
CREATE OR REPLACE FILE FORMAT {schema_name}.PARQUET_FORMAT
    TYPE = PARQUET
    USE_VECTORIZED_SCANNER = TRUE
