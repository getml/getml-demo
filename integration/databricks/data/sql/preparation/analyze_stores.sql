-- Analyze stores and their activity
SELECT
    s.id,
    s.name,
    CAST(s.opened_at AS TIMESTAMP) as opened_at,
    MIN(CAST(o.ordered_at AS TIMESTAMP)) as first_order,
    MAX(CAST(o.ordered_at AS TIMESTAMP)) as last_order,
    COUNT(o.id) as total_orders,
    SUM(COALESCE(o.order_total, 0)) / 100.0 as total_sales
FROM IDENTIFIER(:stores_table) s
LEFT JOIN IDENTIFIER(:orders_table) o ON o.store_id = s.id
GROUP BY s.id, s.name, s.opened_at
ORDER BY CAST(s.opened_at AS TIMESTAMP)
