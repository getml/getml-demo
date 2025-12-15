CREATE WAREHOUSE IF NOT EXISTS {warehouse_name}
WITH
    WAREHOUSE_SIZE = '{warehouse_size}'
    AUTO_SUSPEND = {auto_suspend_seconds}
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;
