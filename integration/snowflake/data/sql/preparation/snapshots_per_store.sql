-- Show snapshots per store
SELECT 
    store_name,
    COUNT(*) as num_snapshots,
    MIN(reference_date) as first_snapshot,
    MAX(reference_date) as last_snapshot
FROM {target_schema}.weekly_stores
GROUP BY store_name
ORDER BY first_snapshot
