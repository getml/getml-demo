-- Create internal stage for uploading local parquet files
-- Used when loading data via session.file.put() instead of external storage integration
CREATE OR REPLACE STAGE {schema_name}.{stage_name}
    FILE_FORMAT = {schema_name}.PARQUET_FORMAT;
