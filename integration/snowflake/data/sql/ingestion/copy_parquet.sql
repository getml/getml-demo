-- Copy Parquet data into table using column name matching
-- MATCH_BY_COLUMN_NAME handles column ordering differences between file and table
COPY INTO {schema_name}.{table_name}
    FROM @{schema_name}.{stage_name}/{table_name}.parquet
    FILE_FORMAT = {schema_name}.PARQUET_FORMAT
    MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
