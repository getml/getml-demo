-- Calculate target - total sales for the following week per store
CREATE TABLE PREPARED.population_weekly_by_store_with_target AS
SELECT 
    p.*,
    COALESCE(
        (
            SELECT SUM(order_total) / 100.0
            FROM RAW.raw_orders o
            WHERE o.store_id = p.store_id
              AND o.ordered_at >= p.prediction_week_start
              AND o.ordered_at <= p.prediction_week_end
        ), 0
    ) as next_week_sales,
    COALESCE(
        (
            SELECT COUNT(*)
            FROM RAW.raw_orders o
            WHERE o.store_id = p.store_id
              AND o.ordered_at >= p.prediction_week_start
              AND o.ordered_at <= p.prediction_week_end
        ), 0
    ) as next_week_orders
FROM PREPARED.population_weekly_by_store p
