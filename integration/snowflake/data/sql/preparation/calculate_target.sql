-- Create view with target: next week's sales per store
--
-- This view joins weekly_stores with pre-aggregated order totals.
-- Target is the sum of order_total for the 7-day window starting at reference_date.
--
-- Window: [reference_date, reference_date + 7 days)
-- - reference_date is Monday 00:00:00 (week start)
-- - Target covers Monday through Sunday of that week
--
-- Optimized: Single aggregation pass instead of correlated subqueries
CREATE OR REPLACE VIEW {target_schema}.{table_name} AS
WITH weekly_order_totals AS (
    SELECT
        store_id,
        DATE_TRUNC('week', TRY_TO_TIMESTAMP(ordered_at)) as week_start,
        SUM(order_total) / 100.0 as week_sales,
        COUNT(*) as week_orders
    FROM {source_schema}.orders
    WHERE ordered_at IS NOT NULL
    GROUP BY store_id, DATE_TRUNC('week', TRY_TO_TIMESTAMP(ordered_at))
)
SELECT
    ws.snapshot_id,
    ws.store_id,
    ws.store_name,
    ws.reference_date,
    ws.year,
    ws.month,
    ws.week_number,
    ws.days_since_open,
    ws.is_full_week_after_opening,
    ws.has_order_activity,
    ws.has_min_history,
    COALESCE(wot.week_sales, 0) as next_week_sales,
    COALESCE(wot.week_orders, 0) as next_week_orders
FROM {target_schema}.weekly_stores ws
LEFT JOIN weekly_order_totals wot
    ON wot.store_id = ws.store_id
    AND wot.week_start = ws.reference_date;
