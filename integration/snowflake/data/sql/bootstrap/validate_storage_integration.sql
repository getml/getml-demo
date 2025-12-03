-- Validate a storage integration can access GCS with list permissions
-- Uses Snowflake's native validation function with full signature
-- Returns JSON with status and action results
SELECT SYSTEM$VALIDATE_STORAGE_INTEGRATION(
    '{integration_name}',
    '{storage_path}',
    '{test_file}',
    'list'
) AS VALIDATION_RESULT
