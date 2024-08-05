"""
This module provides functions for saving and loading getML models to and from Google Cloud Storage (GCS),
as well as managing datasets in Google Cloud Platform (GCP) using Vertex AI. It also includes utility functions
for GCP account management and checking the existence of files in GCS.

Functions:
    save_to_gcs(cfg: Config, file_path: Path) -> None:
        Saves a file to Google Cloud Storage (GCS).

    create_vertex_dataset_tabular(cfg: Config, filename_csv: str) -> aiplatform.TabularDataset:
        Gets or creates a Tabular dataset in Google Cloud Platform (GCP).

    load_from_gcs(cfg: Config, gcs_path: str, folder_name: str) -> str:
        Downloads a file from Google Cloud Storage (GCS) and saves it locally.

    get_account_email() -> str:
        Retrieves the currently configured Google Cloud account email.

    wait_for_training_artifact(cfg: Config) -> None:
        Waits for the model artifact to be saved on GCS (resulting from training) and ensures it exists before proceeding.
"""

import os
from time import sleep

from pathlib import Path
from typing import TYPE_CHECKING, cast
from google.cloud import aiplatform, storage  # type: ignore
from getml.vertexai.utils import run_shell_cmd

if TYPE_CHECKING:
    from getml.vertexai import Config
    from google.cloud.storage.bucket import Bucket  # type: ignore

# ***********************************************************
#  Functions for saving and loading getML Models to/from GCS
# ***********************************************************


def save_to_gcs(cfg: "Config", file_path: Path) -> None:
    """Saves a file to Google Cloud Storage (GCS).

    The file is uploaded to the specified bucket and folder.

    Args:
        cfg (Config): The configuration object.
        file_path (Path): The path of the file to be uploaded.

    Raises:
        ValueError: If the file does not exist.
    """

    if not file_path.exists():
        raise ValueError(f"File {file_path.as_posix()} does not exist.")

    storage_client = storage.Client(project=cfg.GCP_PROJECT_NAME)

    bucket: "Bucket" = storage_client.get_bucket(cfg.BUCKET_NAME)
    blob_path = os.path.join(cfg.BUCKET_DIR_DATASET, file_path.name)
    blob = bucket.blob(blob_path)

    with open(file_path.as_posix(), "rb") as file:
        blob.upload_from_file(file)

    if blob.exists():
        print(f"File {file_path.as_posix()} uploaded successfully to GCS.")
    else:
        print(f"Failed to upload {file_path.as_posix()} to GCS.")


def create_vertex_dataset_tabular(
    cfg: "Config", filename_csv: str
) -> aiplatform.TabularDataset:
    """
    Gets or creates a Tabular dataset in Google Cloud Platform (GCP).

    If the dataset with the specified display name exists in GCP, it is returned.
    Otherwise, a new dataset is created and uploaded to GCS.

    Args:
        cfg (Config): The configuration object.
        filename_csv (str): The name of the CSV file to upload.

    Returns:
        aiplatform.TabularDataset: The GCP dataset object.
    """

    dataset_display_name = f"Dataset_{cfg.GETML_PROJECT_NAME}"

    datasets = aiplatform.TabularDataset.list(
        filter=f"display_name={dataset_display_name}",
        project=cfg.GCP_PROJECT_NAME,
        location=cfg.REGION,
    )
    if datasets:
        # cast because mypy infers the type as VertexAiResourceNoun
        return cast(aiplatform.TabularDataset, datasets[0])
    else:
        save_to_gcs(cfg=cfg, file_path=Path(filename_csv))
        dataset = aiplatform.TabularDataset.create(
            display_name=dataset_display_name,
            gcs_source=cfg.BUCKET_URI_DATASET,
            project=cfg.GCP_PROJECT_NAME,
            location=cfg.REGION,
        )
        return dataset


def load_from_gcs(
    cfg: "Config",
    gcs_path: str,
    folder_name: str,
) -> str:
    """
    Downloads a file from Google Cloud Storage (GCS) and saves it locally.

    Args:
        cfg (Config): The configuration object containing GCP project and bucket information.
        gcs_path (str): The GCS path of the file to download.
        folder_name (str): The local folder to save the file.

    Returns:
        str: The relative path to the downloaded file.

    Raises:
        ValueError: If the GCS path does not prefix with 'gs://'.
    """

    if not gcs_path.startswith("gs://"):
        raise ValueError("The GCS path must begin with 'gs://' prefix.")

    path_file = Path(gcs_path)
    path_file_relative = f"{folder_name}/{path_file.name}"

    storage_client = storage.Client(project=cfg.GCP_PROJECT_NAME)

    # This check is crucial to avoid race conditions introduced by inference workers
    # that are spawn by the AI Platform Prediction container
    if os.path.exists(path_file_relative):
        print(f"File {path_file_relative} already exists locally.")
        return path_file_relative

    print(f"Downloading {path_file_relative} from GCS...")

    # Ensure the local directory exists
    os.makedirs(folder_name, exist_ok=True)

    try:
        bucket: "Bucket" = storage_client.get_bucket(cfg.BUCKET_NAME)
        blob = bucket.blob(path_file_relative)
        # Save the .getml file locally
        with open(path_file_relative, "wb") as file:
            blob.download_to_file(file)
        print(f"Downloaded and saved to {path_file_relative}.")

    except Exception as e:
        print(f"An error occurred: {e}")

    return path_file_relative


def get_account_email() -> str:
    """
    Retrieves the currently configured Google Cloud account email.

    Uses the 'gcloud' command-line tool to get the value of the
    currently configured Google Cloud account email. It runs the command
    'gcloud config get-value account'.

    Returns:
        str: The email address of the currently configured Google Cloud account.
             Returns an empty string if there is an error executing the command.

    Raises:
        subprocess.CalledProcessError: If the 'gcloud' command returns a non-zero exit code.
    """

    command = ["gcloud", "config", "get-value", "account"]

    return run_shell_cmd(command)


def _file_exists_on_gcs(file_path: str = "", bucket_name: str = "") -> bool:
    """
    Checks if the file exists in the GCS bucket.

    Args:
        file_path (str): The path of the file in the GCS bucket.
        bucket (str): The name of the GCS bucket.

    Returns:
        bool: True if the file exists in the GCS bucket, False otherwise.

    Raises:
        Exception: If an error occurs while checking the file existence.
    """

    try:
        storage_client = storage.Client()
        bucket: "Bucket" = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_path)
        if blob.exists():
            return True
        else:
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def wait_for_training_artifact(cfg: "Config") -> None:
    """
    Waits for the model artifact to be saved on GCS (resulting from training).
    Artifact needs to exist before subsequent steps can be executed.

    Args:
        cfg (Config): The configuration object containing GCS bucket information

    Raises:
        FileNotFoundError: If the artifact is not found in the GCS bucket after multiple attempts.
    """

    tries = 200
    wait_time_sec = 10

    file_path = f"{cfg.BUCKET_DIR_MODEL}/{cfg.GETML_PROJECT_NAME}.getml"
    bucket_name = cfg.BUCKET_NAME

    print("Waiting for the training job to be finished..")

    while not _file_exists_on_gcs(file_path=file_path, bucket_name=bucket_name):
        if tries == 0:
            cfg.print_links(["training_jobs", "model_artifact"])
            raise FileNotFoundError(
                "Training artifact (.getml file) not found in the GCS bucket. "
                + "Please ensure the training job has completed successfully "
                + "by checking the training job logs."
            )

        tries -= 1
        sleep(wait_time_sec)

    return None
