# getML Weekly Sales Data Preparation Guide - By Store

**This guide explains how to use the prepared weekly sales forecasting data with getML for store-level predictions.**

The data preparation pipeline creates:

- `weekly_stores` (TABLE): Store-week combinations with `reference_date` (Monday week start)
- `weekly_sales_by_store_with_target` (VIEW): Adds target column (next week's sales)

---

## 1. Weekly Sales View

**View name:** `weekly_sales_by_store_with_target`

| Column | Description |
|--------|-------------|
| `snapshot_id` | Unique identifier for each prediction point |
| `store_id` | The store being predicted |
| `store_name` | Store name (for reference) |
| `reference_date` | Monday (week start) from DATE_TRUNC('week', ...) |
| `year`, `month`, `week_number` | Temporal components |
| `days_since_open` | Days since store opened |
| `is_full_week_after_opening` | True if store had a full week of operation before this week |
| `has_order_activity` | True if store has order data spanning this week |
| `has_min_history` | True if at least 7 days since store opened |
| `next_week_sales` | Target: sum of sales for 7-day window starting at reference_date |
| `next_week_orders` | Number of orders in the target window |

---

## 2. Target Column

**Column name:** `next_week_sales`

- Sum of order_total for the 7-day window: [reference_date, reference_date + 7 days)
- Unit: dollars (already divided by 100)

---

## 3. Time Column

**Column name:** `reference_date`

- Mark this as `time_stamp` role in getML
- Represents Monday 00:00:00 (week start)
- Ensures no data leakage (only past data used for prediction via `ordered_at < reference_date`)

---

## 4. Join Key

**Column name:** `store_id`

- Links weekly sales data to store-specific data

---

## 5. Join Tables

| Table | Join Condition |
|-------|----------------|
| `raw_stores` | `store.id = weekly_sales.store_id` |
| `raw_orders` | `order.store_id = weekly_sales.store_id AND order.ordered_at < reference_date` |
| `raw_customers` | Join through orders |
| `raw_items` | Join through orders |
| `raw_products` | Join through items |
| `raw_tweets` | `tweet.tweeted_at < reference_date` (if relevant to stores) |

---

## 6. Example getML Code

```python
import getml

# Load weekly sales data (one row per store per week)
weekly_sales_by_store = getml.DataFrame.from_db(
    name="weekly_sales_by_store",
    table_name="weekly_sales_by_store_with_target"
)

# Set roles
weekly_sales_by_store.set_role("snapshot_id", getml.data.roles.join_key)
weekly_sales_by_store.set_role("store_id", getml.data.roles.join_key)
weekly_sales_by_store.set_role("reference_date", getml.data.roles.time_stamp)
weekly_sales_by_store.set_role("next_week_sales", getml.data.roles.target)
weekly_sales_by_store.set_role("store_name", getml.data.roles.categorical)

# Boolean flags can be used as features or for filtering
weekly_sales_by_store.set_role(
    ["is_full_week_after_opening", "has_order_activity", "has_min_history"],
    getml.data.roles.categorical
)

# Load peripheral tables
stores = getml.DataFrame.from_db(name="stores", table_name="raw_stores")
stores.set_role("id", getml.data.roles.join_key)
stores.set_role("opened_at", getml.data.roles.time_stamp)

orders = getml.DataFrame.from_db(name="orders", table_name="raw_orders")
orders.set_role("store_id", getml.data.roles.join_key)
orders.set_role("ordered_at", getml.data.roles.time_stamp)

# Define container with store-specific relationships
container = getml.data.Container(population=weekly_sales_by_store)
container.add(
    stores=stores,
    orders=orders,
    # ... other tables
)

# Create propositionalization for store-level features
# getML will automatically aggregate order history per store

# Train model
pipe = getml.Pipeline(...)
pipe.fit(container.train)

# Predict next week's sales for each store
predictions = pipe.predict(container.test)
```

---

## 7. Key Differences from Overall Prediction

- **Row granularity:** Each row represents ONE store's prediction for ONE week
- **Feature scope:** Features will be store-specific (that store's history)
- **Analysis capability:** Can compare store performance, identify store-specific patterns
- **Training data:** More training examples (6 stores × N weeks instead of just N weeks)

---

## 8. Data Quality Flags

The boolean flags can be used to filter training data:

```python
# Only use rows with sufficient history
filtered_weekly_sales = weekly_sales_by_store[weekly_sales_by_store["has_min_history"] == True]

# Or use as features - getML can learn from these patterns
```
