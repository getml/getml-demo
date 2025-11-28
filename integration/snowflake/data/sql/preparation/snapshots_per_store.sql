-- Show snapshots per store
SELECT 
    store_name,
    COUNT(*) as num_snapshots,
    MIN(snapshot_time) as first_snapshot,
    MAX(snapshot_time) as last_snapshot
FROM PREPARED.population_weekly_by_store
GROUP BY store_name
ORDER BY first_snapshot
