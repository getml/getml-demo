-- Statistics per store
SELECT 
    store_name,
    COUNT(*) as num_snapshots,
    AVG(next_week_sales) as avg_weekly_sales,
    MIN(next_week_sales) as min_weekly_sales,
    MAX(next_week_sales) as max_weekly_sales,
    STDDEV(next_week_sales) as stddev_weekly_sales,
    SUM(next_week_orders) as total_orders
FROM {target_schema}.{table_name}
GROUP BY store_name
ORDER BY avg_weekly_sales DESC
