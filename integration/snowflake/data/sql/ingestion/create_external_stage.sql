-- Create external stage pointing to S3 bucket for CSV data ingestion
CREATE OR REPLACE STAGE RAW.{stage_name}
    URL = '{bucket_url}'
    FILE_FORMAT = (
        TYPE = 'CSV'
        FIELD_DELIMITER = ','
        SKIP_HEADER = 1
        FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    )
