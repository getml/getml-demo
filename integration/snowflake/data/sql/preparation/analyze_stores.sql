-- Analyze stores and their activity
SELECT 
    s.id,
    s.name,
    s.opened_at,
    MIN(o.ordered_at) as first_order,
    MAX(o.ordered_at) as last_order,
    COUNT(o.id) as total_orders,
    SUM(COALESCE(o.order_total, 0)) / 100.0 as total_sales
FROM RAW.raw_stores s
LEFT JOIN RAW.raw_orders o ON o.store_id = s.id
GROUP BY s.id, s.name, s.opened_at
ORDER BY s.opened_at
