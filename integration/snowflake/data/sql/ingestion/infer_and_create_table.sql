-- Create table with schema inferred from Parquet file
-- Uses INFER_SCHEMA to automatically detect column names and types
CREATE OR REPLACE TABLE {schema_name}.{table_name}
    USING TEMPLATE (
        SELECT ARRAY_AGG(OBJECT_CONSTRUCT(*))
        FROM TABLE(
            INFER_SCHEMA(
                LOCATION => '@{schema_name}.{stage_name}/{table_name}.parquet',
                FILE_FORMAT => '{schema_name}.PARQUET_FORMAT'
            )
        )
    )
