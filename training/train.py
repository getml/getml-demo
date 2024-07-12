from pathlib import Path
import google.cloud.aiplatform as aiplatform
import getml

from getml.vertexai import (
    Config,
    get_unique_id,
)

cfg = Config.load("config.yaml")

LOG_METRICS = True


def get_path_bucket_folder(bucket_name: str = cfg.BUCKET_NAME) -> str:
    """Returns the path to the Google Cloud Storage (GCS) bucket folder for the current project.

    Determines the runtime environment (Google Cloud or local) and sets the path
    accordingly. In a Google Cloud environment, it returns the GCS bucket path.
    Otherwise, it returns the local directory.

    NOTE: /gcs/ is the FUSE mount point for Google Cloud Storage, mapping buckets to the local file system.
            We assume /gcs/ folder only exists in GCP Environment.

    Args:
        bucket_name (str, optional): The name of the GCS bucket. Defaults to BUCKET_NAME.

    Returns:
        str: The path to the GCS bucket folder if in GCP environment, or the local directory if not.
    """

    if Path("/gcs/").is_dir():
        print("We are in GCP Environment. Using /gcs/ folder.")
        return f"/gcs/{bucket_name}"
    else:
        print("/gcs/ folder does not exist. We are probably in Local Environment.")
        return "."


# ***********************************************************
# Initialize getML
# ***********************************************************

getml.engine.launch()
getml.engine.set_project(cfg.GETML_PROJECT_NAME)

# Load data
population_train, population_test, order, trans, meta = getml.datasets.load_loans(
    roles=True, units=True
)

# Define Data Model
star_schema = getml.data.StarSchema(
    train=population_train, test=population_test, alias="population"
)

star_schema.join(
    trans,
    on="account_id",
    time_stamps=("date_loan", "date"),
)

star_schema.join(
    order,
    on="account_id",
)

star_schema.join(
    meta,
    on="account_id",
)


# ***********************************************************
# Set-up of feature learners, selectors & predictor
# ***********************************************************

fast_prop = getml.feature_learning.FastProp(
    aggregation=getml.feature_learning.FastProp.agg_sets.All,
    loss_function=getml.feature_learning.loss_functions.CrossEntropyLoss,
    num_threads=1,
)

feature_selector = getml.predictors.XGBoostClassifier(n_jobs=1)

# the population is really small, so we set gamma to mitigate overfitting
predictor = getml.predictors.XGBoostClassifier(
    gamma=2,
    n_jobs=1,
)

# ***********************************************************
# Build the pipeline
# ***********************************************************

pipe = getml.pipeline.Pipeline(
    data_model=star_schema.data_model,
    feature_learners=[fast_prop],
    feature_selectors=[feature_selector],
    predictors=predictor,
)

# ***********************************************************
# Train model
# ***********************************************************

pipe.fit(star_schema.train)
getml_score = pipe.score(star_schema.test)

# ***********************************************************
# # Save model
# ***********************************************************

target_dir = Path(f"{get_path_bucket_folder()}/model_artifact")
target_dir.mkdir(parents=True, exist_ok=True)

getml.project.data_frames.save()
getml.project.save(cfg.GETML_PROJECT_NAME, target_dir=target_dir.as_posix())

# ***********************************************************
# Create experiment / Metrics logging
# ***********************************************************

if LOG_METRICS:
    aiplatform.init(
        project=cfg.GCP_PROJECT_NAME,
        experiment="getml-vertexai-loans-notebook",
        location=cfg.REGION,
        experiment_tensorboard=False,
    )

    aiplatform.start_run(f"run-{get_unique_id()}")

    hyperparams = {
        "data_model": "star_schema",
        "feature_selector": "XGBoostClassifier",
        "feature_learners": "fast_prop",
        "num_features": -1,
        "loss_function": "CrossEntropyLoss",
        "predictor": "XGBoostClassifier",
        "target": "default",  # litereally the target column "default"
    }
    aiplatform.log_params(hyperparams)

    # Log system.Metrics
    metrics = {
        "accuracy_train": getml_score[0].accuracy,
        "accuracy_test": getml_score[1].accuracy,
        "auc_train": getml_score[0].auc,
        "auc_test": getml_score[1].auc,
        "cross_entropy_train": getml_score[0].cross_entropy,
        "cross_entropy_test": getml_score[1].cross_entropy,
    }
    aiplatform.log_metrics(metrics)

    aiplatform.end_run()
