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
from pathlib import Path

import getml
from databricks.connect import DatabricksSession

PROJECT_NAME = "databricks_feature_store"

getml.set_project(PROJECT_NAME)

# %%
spark = DatabricksSession.builder.serverless().getOrCreate()

# %%
# Load population table
weekly_sales_by_store_spark = spark.table(
    "workspace.prepared.weekly_sales_by_store_with_target"
)

weekly_sales_by_store = getml.DataFrame.from_arrow(
    weekly_sales_by_store_spark.toArrow(), name="weekly_sales_by_store"
)

# Load peripheral table
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

getml.project.data_frames.save()
container.save()

# %%
container._id

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
pipe.score(container.test)

# %%
# container = getml.data.load_container("uzNVUz")
# pipe = getml.pipeline.load("2aj2Dm")

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
from getml_interpretations import (
    ColumnDescriptionsReport,
    generate_column_descriptions_report,
)

column_descriptions_report_path = Path("column_descriptions_report.json")
jaffle_shop_annotations = Path("annotations.yml")
user_prompt = f"""
Please use the following annotations as source of truth for generating the
column descriptions report:

{jaffle_shop_annotations.read_text()}.
"""

if column_descriptions_report_path.exists():
    column_descriptions_report = ColumnDescriptionsReport.from_json(
        column_descriptions_report_path
    )
else:
    column_descriptions_report: ColumnDescriptionsReport = (
        await generate_column_descriptions_report(
            project_name=PROJECT_NAME,
            pipeline=pipe,
            container=container,
            model="gpt-5-mini",
            user_prompt=user_prompt,
        )
    )
    column_descriptions_report.to_json(column_descriptions_report_path)


# %%
from pathlib import Path

from getml_interpretations import (
    FeatureDescriptionsReport,
    generate_feature_descriptions_report,
)

feature_descriptions_report_path = Path("feature_descriptions_report.json")

user_prompt = """
Feature descriptions are limited to max. 256 characters and 2-3 sentences.
Please ensure that each feature description does not exceed this limit.
Also no bullet points, new lines or line breaks etc.
Keep the descriptions concise, straight-forward and informative.
"""

if feature_descriptions_report_path.exists():
    feature_descriptions_report = FeatureDescriptionsReport.from_json(
        feature_descriptions_report_path
    )
else:
    feature_descriptions_report: FeatureDescriptionsReport = (
        await generate_feature_descriptions_report(
            project_name=PROJECT_NAME,
            pipeline=pipe,
            container=container,
            user_prompt=user_prompt,
            model="gpt-5-mini",
            batch_size=20,
        )
    )
    feature_descriptions_report.to_json(feature_descriptions_report_path)

# %%
column_mapping = {
    desc.name: desc.title
    for desc in feature_descriptions_report.feature_descriptions.values()
}

for old_name, new_name in column_mapping.items():
    features_spark = features_spark.withColumnRenamed(old_name, new_name)


# %%
FEATURES_TABLE_FULL_NAME = "workspace.getml_fs.getml_features_explained"
spark.sql(f"DROP TABLE IF EXISTS {FEATURES_TABLE_FULL_NAME}")

features_spark.write.format("delta").mode("overwrite").option(
    "overwriteSchema", "true"
).saveAsTable(FEATURES_TABLE_FULL_NAME)

spark.sql(f"""
    ALTER TABLE {FEATURES_TABLE_FULL_NAME}
    ALTER COLUMN snapshot_id SET NOT NULL
""")

FEATURES_TABLE_NAME = FEATURES_TABLE_FULL_NAME.split(".")[-1]

spark.sql(f"""
    ALTER TABLE {FEATURES_TABLE_FULL_NAME}
    ADD CONSTRAINT {FEATURES_TABLE_NAME}_pk PRIMARY KEY(snapshot_id)
""")

# %%
for tables in column_descriptions_report.column_descriptions.values():
    for column_name, column_description in tables.items():
        if column_name in features_df.colnames:
            # Escape single quotes to prevent SQL syntax errors
            description = column_description.description.replace("'", "\\'")
            spark.sql(
                f"ALTER TABLE {FEATURES_TABLE_FULL_NAME} CHANGE COLUMN {column_name} COMMENT '{description}'"
            )

# %%
for feature_description in feature_descriptions_report.feature_descriptions.values():
    # Escape single quotes to prevent SQL syntax errors
    description = feature_description.description.replace("'", "\\'")
    spark.sql(
        f"ALTER TABLE {FEATURES_TABLE_FULL_NAME} CHANGE COLUMN {feature_description.title} COMMENT '{description}'"
    )


# %%
# Verify the Feature Table was created
print("Table schema:")
spark.sql(f"DESCRIBE TABLE {FEATURES_TABLE_FULL_NAME}").show(100, truncate=False)

