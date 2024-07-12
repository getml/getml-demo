import os
import subprocess
from pathlib import Path

from google.cloud import aiplatform, storage


# ***********************************************************
#  Functions for saving and loading getML Models to/from GCS
# ***********************************************************


def save_to_gcs(cfg: "Config", file_path: Path) -> None:
    """Saves a file to Google Cloud Storage (GCS).

    The file is uploaded to the specified bucket and folder.

    Args:
        file_path (Path): The path of the file to be uploaded.
        folder_name (str): The name of the folder in the bucket where the file will be saved.
        bucket_name (str, optional): The name of the GCS bucket. Defaults to GCP_BUCKET_NAME.

    Raises:
        ValueError: If the file does not exist.
    """
    file_path.exists() or ValueError(f"File {file_path.as_posix()} does not exist.")

    storage_client = storage.Client(project=cfg.GCP_PROJECT_NAME)

    # Create a blob
    bucket = storage_client.get_bucket(cfg.BUCKET_NAME)
    blob_path = os.path.join(cfg.BUCKET_DIR_DATASET, file_path.name)
    blob = bucket.blob(blob_path)

    # Upload the file from the local directory
    with open(file_path.as_posix(), "rb") as file:
        blob.upload_from_file(file)

    if blob.exists():
        print(f"File {file_path.as_posix()} uploaded successfully to GCS.")
    else:
        print(f"Failed to upload {file_path.as_posix()} to GCS.")


def create_vertex_dataset_tabular(
    cfg: "Config", filename_csv: str
) -> aiplatform.TabularDataset:
    """Gets or creates a Tabular dataset in Google Cloud Platform (GCP).

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
        return datasets[0]
    else:
        save_to_gcs(cfg=cfg, file_path=Path(filename_csv))
        dataset = aiplatform.TabularDataset.create(
            display_name=dataset_display_name,
            gcs_source=cfg.BUCKET_URI,
            project=cfg.GCP_PROJECT_NAME,
            location=cfg.REGION,
        )
        return dataset


def load_from_gcs(
    cfg: "Config",
    gcs_path: str,
    folder_name: str,
) -> str:
    """Downloads a file from Google Cloud Storage (GCS) and saves it locally.

    Downloads the file from the specified GCS path and saves it to the local folder.

    Args:
        gcs_path (str): The GCS path of the file to download.
        folder_name (str): The local folder to save the file.
        bucket_name (str, optional): The name of the GCS bucket. Defaults to GCP_BUCKET_NAME.

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
        # Get the bucket and blob
        bucket = storage_client.get_bucket(cfg.BUCKET_NAME)
        blob = bucket.blob(path_file_relative)

        # Save the .getml file locally
        with open(path_file_relative, "wb") as file:
            blob.download_to_file(file)

        print(f"Downloaded and saved to {path_file_relative}.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return path_file_relative


def get_account_email() -> str:
    command = ["gcloud", "config", "get-value", "account"]

    # Run the command and capture the output
    result = subprocess.run(command, capture_output=True, text=True)

    # Check for errors
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return ""
    else:
        return result.stdout.strip()
