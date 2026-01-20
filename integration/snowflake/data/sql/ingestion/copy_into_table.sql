-- Copy data from staged Parquet file into table
-- Uses MATCH_BY_COLUMN_NAME to map Parquet columns to table columns
COPY INTO {schema_name}.{table_name}
  FROM @{schema_name}.{stage_name}/{source_name}.parquet
  FILE_FORMAT = (FORMAT_NAME = '{schema_name}.PARQUET_FORMAT')
  MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
