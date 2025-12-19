-- Create store-week combinations for weekly sales forecasting
--
-- This table creates the base data for getML: one row per store per week.
-- reference_date is the Monday (week start) derived from date_trunc('week', ordered_at).
--
-- Filtering logic:
-- - Week must be >= store's opened_at date (store existed)
-- - Week must be < last_order_week (exclude incomplete final week)
--
-- Boolean flags for data quality filtering:
-- - is_full_week_after_opening: Store had a full week of operation before this week
-- - has_order_activity: Store has order data spanning this week
-- - has_min_history: At least 7 days since store opened
CREATE OR REPLACE TABLE IDENTIFIER(:weekly_stores_table) AS
WITH store_activity AS (
    SELECT
        s.id as store_id,
        s.name as store_name,
        CAST(s.opened_at AS TIMESTAMP) as opened_at,
        date_add(date_trunc('week', CAST(s.opened_at AS TIMESTAMP)), 7) as first_full_week,
        MIN(CAST(o.ordered_at AS TIMESTAMP)) as first_order_date,
        MAX(CAST(o.ordered_at AS TIMESTAMP)) as last_order_date,
        date_trunc('week', MIN(CAST(o.ordered_at AS TIMESTAMP))) as first_order_week,
        date_trunc('week', MAX(CAST(o.ordered_at AS TIMESTAMP))) as last_order_week
    FROM IDENTIFIER(:stores_table) s
    LEFT JOIN IDENTIFIER(:orders_table) o ON o.store_id = s.id
    GROUP BY s.id, s.name, s.opened_at
),

all_weeks AS (
    SELECT DISTINCT
        date_trunc('week', CAST(ordered_at AS TIMESTAMP)) as reference_date
    FROM IDENTIFIER(:orders_table)
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
    YEAR(reference_date) as year,
    MONTH(reference_date) as month,
    WEEKOFYEAR(reference_date) as week_number,
    DATEDIFF(reference_date, opened_at) as days_since_open,
    CASE WHEN reference_date >= first_full_week THEN true ELSE false END as is_full_week_after_opening,
    CASE WHEN first_order_week IS NOT NULL 
        AND reference_date >= first_order_week
        AND reference_date < last_order_week THEN true ELSE false END as has_order_activity,
    CASE WHEN DATEDIFF(reference_date, opened_at) >= 7 THEN true ELSE false END as has_min_history
FROM store_weeks
ORDER BY reference_date, store_id
