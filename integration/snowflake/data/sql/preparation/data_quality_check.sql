-- Data quality check
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN next_week_sales = 0 THEN 1 ELSE 0 END) as zero_sales,
    SUM(CASE WHEN next_week_orders = 0 THEN 1 ELSE 0 END) as zero_orders,
    SUM(CASE WHEN next_week_sales > 0 AND next_week_orders = 0 THEN 1 ELSE 0 END) as invalid
FROM {target_schema}.{table_name};
