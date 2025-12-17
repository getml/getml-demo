-- Summary of weekly_stores table: counts and per-store breakdown
-- Returns total snapshots, store count, and per-store details in one query
WITH totals AS (
    SELECT
        COUNT(*) as total_snapshots,
        COUNT(DISTINCT store_id) as num_stores
    FROM IDENTIFIER(:weekly_stores_table)
),
per_store AS (
    SELECT
        store_name,
        COUNT(*) as num_snapshots,
        MIN(reference_date) as first_snapshot,
        MAX(reference_date) as last_snapshot
    FROM IDENTIFIER(:weekly_stores_table)
    GROUP BY store_name
)
SELECT
    t.total_snapshots,
    t.num_stores,
    p.store_name,
    p.num_snapshots,
    p.first_snapshot,
    p.last_snapshot
FROM totals t
CROSS JOIN per_store p
ORDER BY p.first_snapshot
