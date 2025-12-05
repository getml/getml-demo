-- Sample snapshots for a specific store
-- Use order_direction="" for oldest first, "DESC" for newest first
SELECT
    snapshot_id,
    reference_date,
    next_week_sales,
    next_week_orders
FROM {target_schema}.{table_name}
WHERE store_name = '{store_name}'
ORDER BY reference_date {order_direction}
LIMIT {limit}
