-- Analyze stores and their activity
SELECT
    s.id,
    s.name,
    TRY_TO_TIMESTAMP(s.opened_at) as opened_at,
    MIN(TRY_TO_TIMESTAMP(o.ordered_at)) as first_order,
    MAX(TRY_TO_TIMESTAMP(o.ordered_at)) as last_order,
    COUNT(o.id) as total_orders,
    SUM(COALESCE(o.order_total, 0)) / 100.0 as total_sales
FROM {source_schema}.stores s
LEFT JOIN {source_schema}.orders o ON o.store_id = s.id
GROUP BY s.id, s.name, s.opened_at
ORDER BY TRY_TO_TIMESTAMP(s.opened_at);
