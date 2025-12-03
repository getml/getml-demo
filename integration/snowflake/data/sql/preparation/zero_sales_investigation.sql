-- Investigate stores with zero sales
SELECT store_name, COUNT(*) as count
FROM {target_schema}.{table_name}
WHERE next_week_sales = 0
GROUP BY store_name
ORDER BY count DESC
