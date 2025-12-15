-- Investigate stores with zero sales
SELECT store_name, COUNT(*) as count
FROM IDENTIFIER(:population_table)
WHERE next_week_sales = 0
GROUP BY store_name
ORDER BY count DESC
