-- Create weekly snapshots per store
-- Only include weeks where:
-- - Store opened BEFORE the week started (store was open at beginning of week)
-- - Store has orders throughout the entire prediction week (store was open entire week)
CREATE TABLE PREPARED.population_weekly_by_store AS
WITH store_weeks AS (
    -- Get all weeks from data
    SELECT DISTINCT 
        DATE_TRUNC('week', ordered_at) as week_start
    FROM RAW.raw_orders
    WHERE ordered_at IS NOT NULL
),
store_activity AS (
    -- Get first full week for each store (week after opening)
    SELECT 
        s.id as store_id,
        s.name as store_name,
        s.opened_at,
        -- First full week is the Monday after opening week
        DATE_TRUNC('week', s.opened_at) + INTERVAL '7 days' as first_full_week,
        MAX(o.ordered_at) as last_order_date,
        DATE_TRUNC('week', MAX(o.ordered_at)) as last_order_week
    FROM RAW.raw_stores s
    LEFT JOIN RAW.raw_orders o ON o.store_id = s.id
    GROUP BY s.id, s.name, s.opened_at
),
valid_store_weeks AS (
    -- Cross join stores with weeks, filter to valid weeks only
    SELECT 
        sa.store_id,
        sa.store_name,
        sw.week_start,
        sw.week_start - INTERVAL '1 second' as snapshot_time,
        sw.week_start as prediction_week_start,
        (sw.week_start + INTERVAL '7 days' - INTERVAL '1 second')
            as prediction_week_end
    FROM store_activity sa
    CROSS JOIN store_weeks sw
    WHERE 
        -- Store was open before this week started
        sw.week_start >= sa.first_full_week
        -- Don't include the last week (might be incomplete)
        AND sw.week_start < sa.last_order_week
)
SELECT 
    ROW_NUMBER() OVER (ORDER BY snapshot_time, store_id) as snapshot_id,
    store_id,
    store_name,
    snapshot_time,
    prediction_week_start,
    prediction_week_end,
    EXTRACT(year FROM snapshot_time) as year,
    EXTRACT(month FROM snapshot_time) as month,
    EXTRACT(week FROM snapshot_time) as week_number
FROM valid_store_weeks
ORDER BY snapshot_time, store_id
