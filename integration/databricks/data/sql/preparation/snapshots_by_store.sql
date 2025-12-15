-- Sample snapshots for a specific store
SELECT
    snapshot_id,
    reference_date,
    next_week_sales,
    next_week_orders
FROM IDENTIFIER(:population_table)
WHERE store_name = :store_name
ORDER BY reference_date {order_direction}
LIMIT :limit
