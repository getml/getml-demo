-- Create view with target: next week's sales per store
--
-- This view joins weekly_stores with raw_orders to calculate the target variable.
-- Target is the sum of order_total for the 7-day window starting at reference_date.
--
-- Window: [reference_date, reference_date + 7 days)
-- - reference_date is Monday 00:00:00 (week start)
-- - Target covers Monday through Sunday of that week
CREATE OR REPLACE VIEW PREPARED.population_weekly_by_store_with_target AS
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
    COALESCE(
        (
            SELECT SUM(o.order_total) / 100.0
            FROM RAW.raw_orders o
            WHERE o.store_id = ws.store_id
              AND o.ordered_at >= ws.reference_date
              AND o.ordered_at < ws.reference_date + INTERVAL '7 days'
        ), 0
    ) as next_week_sales,
    COALESCE(
        (
            SELECT COUNT(*)
            FROM RAW.raw_orders o
            WHERE o.store_id = ws.store_id
              AND o.ordered_at >= ws.reference_date
              AND o.ordered_at < ws.reference_date + INTERVAL '7 days'
        ), 0
    ) as next_week_orders
FROM PREPARED.weekly_stores ws;
