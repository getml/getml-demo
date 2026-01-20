# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.7
#   kernelspec:
#     display_name: snowflake-feature-store-notebooks
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Build Snowflake Feature Store with getML

# %% [markdown]
# This notebook demonstrates how to build a Snowflake Feature Store using getML's automated feature engineering. We'll load data from Snowflake, generate time-series features with FastProp, and register them as a versioned FeatureView with full metadata enrichment.
#
# **Prerequisites:** Run `mise env --dotenv > notebooks/.env` to generate environment configuration.

# %%
import os

import getml
from snowflake.snowpark import Session

PROJECT_NAME = "snowflake_feature_store"

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")

# %%

getml.set_project(PROJECT_NAME)

# %% [markdown]
# ## Setup and Data Loading
#
# Connect to Snowflake and load the population table (weekly sales by store) and peripheral table (orders) into getML using Arrow for efficient data transfer.

# %%


connection_params = {
    "account": SNOWFLAKE_ACCOUNT,
    "user": SNOWFLAKE_USER,
    "password": SNOWFLAKE_PASSWORD,
    "role": SNOWFLAKE_ROLE,
    "warehouse": SNOWFLAKE_WAREHOUSE,
    "database": SNOWFLAKE_DATABASE,
    "schema": SNOWFLAKE_SCHEMA,
}

session = Session.builder.configs(connection_params).create()

# %%
weekly_sales_by_store = getml.DataFrame.from_arrow(
    session.table("PREPARED.WEEKLY_SALES_BY_STORE_WITH_TARGET").to_arrow(),
    name="weekly_sales_by_store",
)

orders = getml.DataFrame.from_arrow(
    session.table("RAW.ORDERS").to_arrow(),
    name="orders",
)

# %% [markdown]
# ## Annotations
#
# Define semantic roles for each column. Roles tell getML how to use columns:
# `join_key` for entity relationships, `time_stamp` for temporal ordering,
# `target` for prediction, and `numerical`/`categorical` for feature types.

# %%
weekly_sales_by_store.set_role(
    cols=["STORE_ID", "SNAPSHOT_ID"], role=getml.data.roles.join_key
)
weekly_sales_by_store.set_role(cols="REFERENCE_DATE", role=getml.data.roles.time_stamp)
weekly_sales_by_store.set_role(cols="NEXT_WEEK_SALES", role=getml.data.roles.target)
weekly_sales_by_store.set_role(
    cols=[
        "STORE_NAME",
        "YEAR",
        "MONTH",
        "WEEK_NUMBER",
        "IS_FULL_WEEK_AFTER_OPENING",
        "HAS_ORDER_ACTIVITY",
        "HAS_MIN_HISTORY",
    ],
    role=getml.data.roles.categorical,
)
weekly_sales_by_store.set_role(
    cols=["DAYS_SINCE_OPEN", "NEXT_WEEK_ORDERS"], role=getml.data.roles.numerical
)


# %%
orders.set_role(cols=["STORE_ID", "ID", "CUSTOMER"], role=getml.data.roles.join_key)
orders.set_role(
    cols="ORDERED_AT",
    role=getml.data.roles.time_stamp,
    time_formats=["%Y-%m-%dT%H:%M:%S"],
)
orders.set_role(
    cols=["SUBTOTAL", "ORDER_TOTAL", "TAX_PAID"], role=getml.data.roles.numerical
)

# %%
weekly_sales_by_store

# %%
orders

# %% [markdown]
# ## Data Model
#
# Define a star schema with `weekly_sales_by_store` as the population table and `orders` as a peripheral table joined on `STORE_ID`. The join uses a 30-day memory window to aggregate historical order data up to each reference date.

# %%
validation_begin = getml.data.time.datetime(2023, 1, 1)
test_begin = getml.data.time.datetime(2024, 1, 1)

split = getml.data.split.time(
    population=weekly_sales_by_store,
    time_stamp="REFERENCE_DATE",
    validation=validation_begin,
    test=test_begin,
)

weekly_sales_by_store_train = weekly_sales_by_store[split == "train"]
weekly_sales_by_store_validation = weekly_sales_by_store[split == "validation"]
weekly_sales_by_store_test = weekly_sales_by_store[split == "test"]

print(
    f"Training set size: {len(weekly_sales_by_store_train)}"
    f"\nValidation set size: {len(weekly_sales_by_store_validation)}"
    f"\nTest set size: {len(weekly_sales_by_store_test)}"
)

# %%
weekly_sales_by_store_validation

# %%
data_model = getml.data.DataModel(
    population=weekly_sales_by_store_train.to_placeholder()
)

data_model.add(getml.data.to_placeholder(orders=orders))

data_model.weekly_sales_by_store.join(
    right=data_model.orders,
    on="STORE_ID",
    time_stamps=("REFERENCE_DATE", "ORDERED_AT"),
    relationship=getml.data.relationship.one_to_many,
    memory=getml.data.time.days(30),
)

# %%
container = getml.data.Container(
    train=weekly_sales_by_store_train,
    validation=weekly_sales_by_store_validation,
    test=weekly_sales_by_store_test,
)

container.add(orders=orders)
container.save()

getml.project.data_frames.save()

# %% [markdown]
# ## Training
#
# Train a pipeline using Multirel for automated feature learning and XGBoost for prediction. Multirel generates time-series aggregations from the relational data model.

# %%
fast_prop = getml.feature_learning.Multirel()

xgboost = getml.predictors.XGBoostRegressor()

pipe = getml.Pipeline(
    data_model=data_model,
    feature_learners=fast_prop,
    predictors=xgboost,
)

pipe.fit(container.train)

# %%
predictions = pipe.predict(container.test)
n_features = len(pipe.features)
pipe.score(container.test)

# %% [markdown]
# ## Feature Export
#
# Export the generated features to Snowflake and register them as a FeatureView. This section also generates human-readable feature descriptions using an LLM to make features discoverable in Snowflake's Universal Search.

# %%
from pathlib import Path

from getml_interpretations import generate_column_descriptions_report

jaffle_shop_annotations = Path("annotations.yml")
user_prompt = f"""
Please use the following annotations as source of truth for generating the
column descriptions report:

{jaffle_shop_annotations.read_text()}.
"""

column_descriptions_report = await generate_column_descriptions_report(
    project_name=PROJECT_NAME,
    pipeline=pipe,
    container=container,
    model="gpt-5-mini",
    user_prompt=user_prompt,
)

# %%
from getml_interpretations import (
    FeatureDescriptionsReport,
    generate_feature_descriptions_report,
)

user_prompt = """
Feature descriptions are limited to max. 256 characters and 2-3 sentences.
Please ensure that each feature description does not exceed this limit.
Also no bullet points, new lines or line breaks etc.
Keep the descriptions concise, straight-forward and informative.
"""

feature_descriptions_report = await generate_feature_descriptions_report(
    project_name=PROJECT_NAME,
    pipeline=pipe,
    container=container,
    column_descriptions_report=column_descriptions_report,
    user_prompt=user_prompt,
    model="gpt-5-mini",
    batch_size=20,
)

feature_descriptions_report = FeatureDescriptionsReport.model_validate_json(
    Path("feature_descriptions_report.json").read_text()
)


# %%
FEATURE_STORE_NAME = "SNOWFLAKE_FEATURE_STORE"
FEATURE_STORE_VERSION = "5"

# %%
features = pipe.transform(
    population_table=weekly_sales_by_store,
    peripheral_tables=[orders],
    df_name="weekly_sales_features_full",
)

name_to_title = {
    feat.name: feat.title
    for feat in feature_descriptions_report.feature_descriptions.values()
}
features_pd = features.to_pandas().rename(columns=name_to_title)

session.write_pandas(
    df=features_pd,
    table_name="GETML_FEATURES",
    schema="GETML_FS",
    auto_create_table=True,
    overwrite=True,
)

# %%
from snowflake.ml.feature_store import CreationMode, Entity, FeatureStore, FeatureView

features_snowpark_df = session.table("GETML_FS.GETML_FEATURES")

snowflake_feature_store = FeatureStore(
    session=session,
    database=SNOWFLAKE_DATABASE,
    name="GETML_FS",
    default_warehouse=SNOWFLAKE_WAREHOUSE,
    creation_mode=CreationMode.CREATE_IF_NOT_EXIST,
)

store_entity = Entity(name="STORE_SNAPSHOT", join_keys=["STORE_ID", "SNAPSHOT_ID"])
snowflake_feature_store.register_entity(store_entity)


# %%
from snowflake.snowpark import Session


def set_column_comments(
    session: Session,
    table_fqn: str,
    comments: dict[str, str],
) -> None:
    clauses = []
    params = [table_fqn]
    for col, comment in comments.items():
        clauses.append(f"COLUMN {col} COMMENT ?")
        params.append(comment)

    body = ", ".join(clauses)

    session.sql(
        f"ALTER TABLE IDENTIFIER(?) MODIFY {body}",
        params=params,
    ).collect()


def set_column_tags(
    session: Session,
    object_type: str,  # "TABLE" or "VIEW"
    object_name: str,
    column_name: str,
    tags: dict[str, str],
) -> None:
    for tag_name, tag_value in tags.items():
        session.sql(
            f"ALTER {object_type} IDENTIFIER(?)"
            f"MODIFY COLUMN {column_name}"
            f"SET TAG {tag_name} = ?",
            params=[object_name, tag_value],
        ).collect()


# %%
# refresh_freq=None means features are externally managed
weekly_sales_feature_view = FeatureView(
    name="weekly_sales_features",
    entities=[store_entity],
    feature_df=features_snowpark_df,
    refresh_freq=None,
    desc="Features generated by getML for weekly sales prediction",
).attach_feature_desc(
    {
        feat.title: feat.description
        for feat in feature_descriptions_report.feature_descriptions.values()
    }
)

registered_feature_view = snowflake_feature_store.register_feature_view(
    feature_view=weekly_sales_feature_view,
    version=FEATURE_STORE_VERSION,
    overwrite=True,
)

# %% [markdown]
# ### Metadata Enrichment
#
# We enrich Snowflake objects with comments, semantic tags, and feature provenance metadata for governance and discoverability. The implementation details are in `metadata_enrichment.py`.

# %%
import yaml
from metadata import (
    create_feature_metadata_table,
    enrich_feature_table,
    enrich_object,
    parse_annotations,
    parse_features,
    setup_getml_tags,
)

PIPELINE_NAME = "weekly_sales_features"

tables = parse_annotations(yaml.safe_load(jaffle_shop_annotations.read_text()))
column_descs = column_descriptions_report.model_dump()["column_descriptions"]
features = parse_features(feature_descriptions_report.model_dump())

orders_table = session.table("RAW.ORDERS")
setup_getml_tags(orders_table)

enrich_object(
    orders_table,
    description=tables["raw_orders"].description,
    column_comments=column_descs["orders"],
    tags={"GETML_PIPELINE": PIPELINE_NAME, "GETML_ROLE": "peripheral"},
)

enrich_object(
    session.table("PREPARED.WEEKLY_SALES_BY_STORE_WITH_TARGET"),
    object_type="VIEW",
    description=tables["weekly_sales_by_store"].description,
    column_comments=column_descs["weekly_sales_by_store"],
    tags={"GETML_PIPELINE": PIPELINE_NAME, "GETML_ROLE": "population"},
)

features_table = session.table("GETML_FS.GETML_FEATURES")
enrich_object(
    features_table,
    description=f"ML features generated by getML Multirel for weekly sales prediction. Contains {n_features} time-series features derived from 30-day rolling aggregations of order data.",
    tags={"GETML_PIPELINE": PIPELINE_NAME, "GETML_ROLE": "features"},
)
enrich_feature_table(
    features_table,
    feature_view_fqn=registered_feature_view.fully_qualified_name(),
    features=features,
    join_key_comments={
        "STORE_ID": "Store identifier. Join key linking to weekly_sales_by_store population table.",
        "SNAPSHOT_ID": "Snapshot identifier. Join key for row-level entity identification.",
    },
)

metadata_table = create_feature_metadata_table(features_table, features)
enrich_object(
    metadata_table,
    description="getML feature metadata including SQL provenance for GETML_FEATURES table",
    tags={"GETML_PIPELINE": PIPELINE_NAME, "GETML_ROLE": "metadata"},
)

# %%
from snowflake.snowpark.functions import col, concat, lit

info_schema = session.table("INFORMATION_SCHEMA.TABLES")
info_schema.filter(col("TABLE_SCHEMA").isin("RAW", "PREPARED", "GETML_FS")).select(
    concat(col("TABLE_SCHEMA"), lit("."), col("TABLE_NAME")).alias("OBJECT"),
    col("COMMENT"),
).show()

# %%
session.table("GETML_FS.GETML_FEATURES").describe().show(3)

# %%
feature_metadata = session.table("GETML_FS.FEATURE_METADATA")
feature_metadata.select(
    "FEATURE_NAME", "ORIGINAL_NAME", "IMPORTANCE", "CORRELATION"
).sort(col("IMPORTANCE").desc()).limit(5).show()

# %%
feature_metadata.filter(col("IMPORTANCE") > 0).select("FEATURE_NAME", "SQL_CODE").sort(
    col("IMPORTANCE").desc()
).limit(1).show()

# %% [markdown]
# ## Summary
#
# This notebook created a complete feature engineering pipeline:
# - **52 features** generated from order history using Multirel
# - **FeatureView** registered in Snowflake Feature Store with versioning
# - **Metadata** enriched with descriptions, importance scores, and SQL provenance
