import json
from dataclasses import dataclass

import pandas as pd
from snowflake.snowpark import Table


@dataclass
class TableAnnotation:
    name: str
    description: str | None = None
    snowflake_fqn: str | None = None
    object_type: str | None = None
    role: str | None = None


def parse_annotations(data: dict) -> dict[str, TableAnnotation]:
    return {
        t["name"]: TableAnnotation(
            name=t["name"],
            description=t.get("description"),
            snowflake_fqn=t.get("snowflake_fqn"),
            object_type=t.get("type"),
            role=t.get("role"),
        )
        for t in data["tables"]
    }


@dataclass
class Feature:
    name: str
    title: str
    description: str
    description_confidence: str
    importance: float
    correlation: float
    target: str
    sql: str


def parse_features(data: dict) -> list[Feature]:
    return [
        Feature(
            name=name,
            title=data["feature_descriptions"][name]["title"],
            description=data["feature_descriptions"][name]["description"],
            description_confidence=data["feature_descriptions"][name]["description_confidence"],
            importance=feat["importance"],
            correlation=feat["correlation"],
            target=feat["target"],
            sql=feat["sql"],
        )
        for name, feat in data["features"].items()
    ]


def get_fqn(table: Table) -> str:
    return ".".join(table.queries["queries"][0].split()[-1].split(".")[-2:])


def enrich_object(
    table: Table,
    *,
    object_type: str = "TABLE",
    description: str | None = None,
    column_comments: dict[str, str] | None = None,
    tags: dict[str, str] | None = None,
) -> None:
    fqn = get_fqn(table)

    if description:
        table.session.sql(f"COMMENT ON {object_type} {fqn} IS '{description}'").collect()

    for col, comment in (column_comments or {}).items():
        table.session.sql(f"COMMENT ON COLUMN {fqn}.{col} IS '{comment}'").collect()

    for tag, value in (tags or {}).items():
        table.session.sql(f"ALTER {object_type} {fqn} SET TAG GETML_FS.{tag} = '{value}'").collect()


def enrich_feature_table(
    features_table: Table,
    feature_view_fqn: str,
    features: list[Feature],
    *,
    join_key_comments: dict[str, str] | None = None,
) -> None:
    fqn = get_fqn(features_table)
    session = features_table.session

    for feat in features:
        col = feat.title.upper()
        session.sql(f"COMMENT ON COLUMN {fqn}.{col} IS '{feat.description}'").collect()
        for tag, value in {
            "GETML_ORIGINAL_NAME": feat.name,
            "GETML_IMPORTANCE": f"{feat.importance:.6f}",
            "GETML_CORRELATION": f"{feat.correlation:.4f}",
            "GETML_TARGET": feat.target,
        }.items():
            session.sql(
                f"ALTER VIEW {feature_view_fqn} MODIFY COLUMN {col} SET TAG GETML_FS.{tag} = '{value}'"
            ).collect()

    for col, comment in (join_key_comments or {}).items():
        session.sql(f"COMMENT ON COLUMN {fqn}.{col} IS '{comment}'").collect()


def create_feature_metadata_table(
    source_table: Table, features: list[Feature], *, schema: str = "GETML_FS"
) -> Table:
    session = source_table.session
    rows = [
        {
            "FEATURE_NAME": f.title.upper(),
            "ORIGINAL_NAME": f.name,
            "IMPORTANCE": f.importance,
            "CORRELATION": f.correlation,
            "TARGET": f.target,
            "DESCRIPTION": f.description,
            "DESCRIPTION_CONFIDENCE": f.description_confidence,
            "SQL_CODE": f.sql,
            "FULL_METADATA": json.dumps(vars(f)),
        }
        for f in features
    ]

    session.write_pandas(
        pd.DataFrame(rows),
        table_name="FEATURE_METADATA",
        schema=schema,
        auto_create_table=True,
        overwrite=True,
    )
    return session.table(f"{schema}.FEATURE_METADATA")


def setup_getml_tags(table: Table, schema: str = "GETML_FS") -> None:
    for name, comment, allowed in [
        ("GETML_ORIGINAL_NAME", "Original getML feature name (e.g., feature_1_1)", None),
        ("GETML_IMPORTANCE", "XGBoost feature importance score", None),
        ("GETML_CORRELATION", "Pearson correlation with target variable", None),
        ("GETML_TARGET", "Target variable this feature predicts", None),
        ("GETML_PIPELINE", "Name of getML pipeline using this data", None),
        ("GETML_ROLE", "Role of table in getML data model", ["population", "peripheral", "features", "metadata"]),
    ]:
        allowed_clause = f"ALLOWED_VALUES {', '.join(repr(v) for v in allowed)} " if allowed else ""
        table.session.sql(f"CREATE TAG IF NOT EXISTS {schema}.{name} {allowed_clause}COMMENT = '{comment}'").collect()
