-- Create a GCS storage integration for accessing Google Cloud Storage buckets
-- Requires ACCOUNTADMIN role or CREATE INTEGRATION privilege
CREATE OR REPLACE STORAGE INTEGRATION {integration_name}
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'GCS'
    ENABLED = TRUE
    STORAGE_ALLOWED_LOCATIONS = ('{allowed_location}')
