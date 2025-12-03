-- Create store-week combinations for weekly sales forecasting
--
-- This table creates the base data for getML: one row per store per week.
-- reference_date is the Monday (week start) derived from DATE_TRUNC('week', ordered_at).
--
-- Filtering logic:
-- - Week must be >= store's opened_at date (store existed)
-- - Week must be < last_order_week (exclude incomplete final week)
--
-- Boolean flags for data quality filtering:
-- - is_full_week_after_opening: Store had a full week of operation before this week
-- - has_order_activity: Store has order data spanning this week
-- - has_min_history: At least 7 days since store opened
CREATE TABLE {target_schema}.weekly_stores AS
WITH store_activity AS (
    SELECT 
        s.id as store_id,
        s.name as store_name,
        s.opened_at,
        DATE_TRUNC('week', s.opened_at) + INTERVAL '7 days' as first_full_week,
        MIN(o.ordered_at) as first_order_date,
        MAX(o.ordered_at) as last_order_date,
        DATE_TRUNC('week', MIN(o.ordered_at)) as first_order_week,
        DATE_TRUNC('week', MAX(o.ordered_at)) as last_order_week
    FROM {source_schema}.raw_stores s
    LEFT JOIN {source_schema}.raw_orders o ON o.store_id = s.id
    GROUP BY s.id, s.name, s.opened_at
),

all_weeks AS (
    SELECT DISTINCT 
        DATE_TRUNC('week', ordered_at) as reference_date
    FROM {source_schema}.raw_orders
    WHERE ordered_at IS NOT NULL
),

store_weeks AS (
    SELECT 
        sa.store_id,
        sa.store_name,
        w.reference_date,
        sa.opened_at,
        sa.first_full_week,
        sa.first_order_week,
        sa.last_order_week
    FROM store_activity sa
    CROSS JOIN all_weeks w
    WHERE w.reference_date >= sa.opened_at
      AND w.reference_date < sa.last_order_week
)

SELECT 
    ROW_NUMBER() OVER (ORDER BY reference_date, store_id) as snapshot_id,
    store_id,
    store_name,
    reference_date,
    EXTRACT(year FROM reference_date) as year,
    EXTRACT(month FROM reference_date) as month,
    EXTRACT(week FROM reference_date) as week_number,
    DATEDIFF('day', opened_at, reference_date) as days_since_open,
    reference_date >= first_full_week as is_full_week_after_opening,
    first_order_week IS NOT NULL 
        AND reference_date >= first_order_week
        AND reference_date < last_order_week as has_order_activity,
    DATEDIFF('day', opened_at, reference_date) >= 7 as has_min_history
FROM store_weeks
ORDER BY reference_date, store_id;
