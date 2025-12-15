-- Overall statistics
SELECT 
    COUNT(*) as total_snapshots,
    COUNT(DISTINCT store_id) as num_stores,
    AVG(next_week_sales) as avg_weekly_sales,
    SUM(next_week_sales) as total_sales,
    SUM(next_week_orders) as total_orders
FROM {target_schema}.{table_name};
