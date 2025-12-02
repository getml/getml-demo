-- Sample data - first 5 snapshots for a specific store
SELECT 
    snapshot_id,
    reference_date,
    next_week_sales,
    next_week_orders
FROM PREPARED.population_weekly_by_store_with_target
WHERE store_name = '{store_name}'
ORDER BY reference_date
LIMIT 5
