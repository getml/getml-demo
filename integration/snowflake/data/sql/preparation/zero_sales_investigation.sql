-- Investigate stores with zero sales
SELECT store_name, COUNT(*) as count
FROM PREPARED.population_weekly_by_store_with_target
WHERE next_week_sales = 0
GROUP BY store_name
ORDER BY count DESC
