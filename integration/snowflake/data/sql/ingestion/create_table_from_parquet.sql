-- Create table with schema inferred from Parquet file
-- Uses INFER_SCHEMA to detect column names and types from the Parquet metadata
-- Column names are uppercased to match Snowflake conventions (unquoted identifiers)
CREATE OR REPLACE TABLE {schema_name}.{table_name}
  USING TEMPLATE (
    SELECT ARRAY_AGG(OBJECT_CONSTRUCT(
      'COLUMN_NAME', UPPER(COLUMN_NAME),
      'TYPE', TYPE,
      'NULLABLE', NULLABLE
    ))
      FROM TABLE(
        INFER_SCHEMA(
          LOCATION=>'@{schema_name}.{stage_name}/{source_name}.parquet',
          FILE_FORMAT=>'{schema_name}.PARQUET_FORMAT'
        )
      ));
