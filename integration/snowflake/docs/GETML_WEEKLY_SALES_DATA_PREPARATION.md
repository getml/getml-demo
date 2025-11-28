# getML Weekly Sales Data Preparation Guide - By Store

**This guide explains how to use the prepared weekly sales forecasting data with getML for store-level predictions.**

The data preparation pipeline creates population tables with weekly snapshots (Sunday nights) per store, calculating the target as total sales for the following week. Only full weeks where the store was open for the entire week are included.

---

## 1. Population Table

**Table name:** `population_weekly_by_store_with_target`

| Column | Description |
|--------|-------------|
| `snapshot_id` | Unique identifier for each prediction point |
| `store_id` | The store being predicted |
| `store_name` | Store name (for reference) |
| `snapshot_time` | The time of prediction (Sunday 23:59:59) |
| `prediction_week_start` | Start of the week being predicted |
| `prediction_week_end` | End of the week being predicted |

---

## 2. Target Column

**Column name:** `next_week_sales`

- This is the sum of sales for the following 7 days **for that specific store**
- Unit: dollars (already divided by 100)

---

## 3. Time Column

**Column name:** `snapshot_time`

- Mark this as `time_stamp` role in getML
- Ensures no data leakage (only past data used for prediction)

---

## 4. Join Key

**Column name:** `store_id`

- Links population to store-specific data

---

## 5. Join Tables

| Table | Join Condition |
|-------|----------------|
| `raw_stores` | `store.id = population.store_id` |
| `raw_orders` | `order.store_id = population.store_id AND order.ordered_at <= snapshot_time` |
| `raw_customers` | Join through orders |
| `raw_items` | Join through orders |
| `raw_products` | Join through items |
| `raw_tweets` | `tweet.tweeted_at <= snapshot_time` (if relevant to stores) |

---

## 6. Example getML Code

```python
import getml

# Load population (one row per store per week)
population = getml.DataFrame.from_db(
    name="population",
    table_name="population_weekly_by_store_with_target"
)

# Set roles
population.set_role("snapshot_id", getml.data.roles.join_key)
population.set_role("store_id", getml.data.roles.join_key)
population.set_role("snapshot_time", getml.data.roles.time_stamp)
population.set_role("next_week_sales", getml.data.roles.target)
population.set_role("store_name", getml.data.roles.categorical)

# Load peripheral tables
stores = getml.DataFrame.from_db(name="stores", table_name="raw_stores")
stores.set_role("id", getml.data.roles.join_key)
stores.set_role("opened_at", getml.data.roles.time_stamp)

orders = getml.DataFrame.from_db(name="orders", table_name="raw_orders")
orders.set_role("store_id", getml.data.roles.join_key)
orders.set_role("ordered_at", getml.data.roles.time_stamp)

# Define container with store-specific relationships
container = getml.data.Container(population=population)
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
