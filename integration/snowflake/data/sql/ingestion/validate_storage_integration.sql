-- Validate a storage integration configuration
-- Returns success message or error details
SELECT SYSTEM$VALIDATE_STORAGE_INTEGRATION('{integration_name}') AS validation_result
