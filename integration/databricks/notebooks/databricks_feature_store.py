# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: getml-demo
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Prerequisites
#
# Before running this notebook:
#
# 1. Authenticate with Databricks:
# ```bash
# databricks auth login
# ```
#
# 2. Prepare the data:
# ```bash
# uv run --group databricks python -m integration.databricks.prepare_jaffle_shop_data_for_databricks
# ```
#
# This will load raw data from GCS and create the weekly sales forecasting population table.

# %% [markdown]
# ## Setup and Data Loading

# %%
import getml
from databricks.connect import DatabricksSession

getml.set_project("databricks_feature_store")

# %%
spark = DatabricksSession.builder.serverless().getOrCreate()

# %%
weekly_sales_by_store_spark = spark.table(
    "workspace.prepared.weekly_sales_by_store_with_target"
)

weekly_sales_by_store = getml.DataFrame.from_arrow(
    weekly_sales_by_store_spark.toArrow(), name="weekly_sales_by_store"
)

# # Load orders table
orders_spark = spark.table("workspace.raw.raw_orders")
orders = getml.DataFrame.from_arrow(orders_spark.toArrow(), name="orders")

# %% [markdown]
# ## getML Annotations

# %%
weekly_sales_by_store.set_role(
    cols=["store_id", "snapshot_id"], role=getml.data.roles.join_key
)
weekly_sales_by_store.set_role(cols="reference_date", role=getml.data.roles.time_stamp)
weekly_sales_by_store.set_role(cols="next_week_sales", role=getml.data.roles.target)
weekly_sales_by_store.set_role(
    cols=[
        "store_name",
        "year",
        "month",
        "week_number",
        "is_full_week_after_opening",
        "has_order_activity",
        "has_min_history",
    ],
    role=getml.data.roles.categorical,
)
weekly_sales_by_store.set_role(
    cols=["days_since_open", "next_week_orders"], role=getml.data.roles.numerical
)
weekly_sales_by_store


# %%
orders.set_role(cols=["store_id", "id", "customer"], role=getml.data.roles.join_key)
orders.set_role(
    cols="ordered_at",
    role=getml.data.roles.time_stamp,
    time_formats=["%Y-%m-%dT%H:%M:%S"],
)
orders.set_role(
    cols=["subtotal", "order_total", "tax_paid"], role=getml.data.roles.numerical
)
orders

# %% [markdown]
# ## getML Data Model

# %%
validation_begin = getml.data.time.datetime(2023, 1, 1)
test_begin = getml.data.time.datetime(2024, 1, 1)

split = getml.data.split.time(
    population=weekly_sales_by_store,
    time_stamp="reference_date",
    validation=validation_begin,
    test=test_begin,
)

# Filter dataframes using the split column
weekly_sales_by_store_train = weekly_sales_by_store[split == "train"]
weekly_sales_by_store_validation = weekly_sales_by_store[split == "validation"]
weekly_sales_by_store_test = weekly_sales_by_store[split == "test"]

print(
    f"Training set size: {len(weekly_sales_by_store_train)}"
    f"\nValidation set size: {len(weekly_sales_by_store_validation)}"
    f"\nTest set size: {len(weekly_sales_by_store_test)}"
)

# %%
data_model = getml.data.DataModel(
    population=weekly_sales_by_store_train.to_placeholder("weekly_sales_by_store")
)

# Add all peripheral tables
data_model.add(
    getml.data.to_placeholder(
        orders=orders,
    )
)

# Define relationships using joins
data_model.weekly_sales_by_store.join(
    right=data_model.orders,
    on="store_id",
    time_stamps=("reference_date", "ordered_at"),
    relationship=getml.data.relationship.one_to_many,
    memory=getml.data.time.days(30),
)

# %%
container = getml.data.Container(
    train=weekly_sales_by_store_train,
    validation=weekly_sales_by_store_validation,
    test=weekly_sales_by_store_test,
)

# Add peripheral tables with aliases matching the data model placeholders
container.add(
    orders=orders,
)
# container.save()
# getml.project.data_frames.save()

# %% [markdown]
# ## Training

# %%
fast_prop = getml.feature_learning.FastProp()

predictor = getml.predictors.XGBoostRegressor(
    n_jobs=0,
)

pipe = getml.Pipeline(
    data_model=data_model,
    feature_learners=[
        fast_prop,
    ],
    predictors=[predictor],
)

pipe.fit(container.train)

# %%
# predictions = pipe.predict(container.test)

# # Calculate metrics
# scores = pipe.score(container.test)
# scores

# %%
pipe = getml.pipeline.load("CzNABb")

# %% [markdown]
# ## Feature Export

# %%
# Transform features using getML pipeline
features_df = pipe.transform(
    population_table=weekly_sales_by_store,
    peripheral_tables=[orders],
    df_name="features",
)


features_spark = spark.createDataFrame(features_df.to_arrow())

features_df

# %%
spark.sql("DROP TABLE IF EXISTS workspace.getml_fs.getml_features")

features_spark.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable("workspace.getml_fs.getml_features")

spark.sql("""
    ALTER TABLE workspace.getml_fs.getml_features
    ALTER COLUMN snapshot_id SET NOT NULL
""")

spark.sql("""
    ALTER TABLE workspace.getml_fs.getml_features
    ADD CONSTRAINT getml_features_pk PRIMARY KEY(snapshot_id)
""")

# %%
for feature in pipe.features:
    spark.sql(
        f"ALTER TABLE workspace.getml_fs.getml_features CHANGE COLUMN {feature.name} COMMENT '{feature.sql}'"
    )

# %%
# Verify the Feature Table was created
print("Table schema:")
spark.sql("DESCRIBE TABLE workspace.getml_fs.getml_features").show(100, truncate=False)

