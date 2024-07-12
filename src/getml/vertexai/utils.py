"""
This module contains utility functions and a sample method to make predictions using Google AI Platform.
It provides functionalities to generate unique identifiers, determine the storage path based on the runtime
environment, and predict using a custom-trained model on AI Platform.

Functions:
    get_unique_id() -> str:
        Generates a unique identifier based on the current date and time.

    get_path_bucket_folder(bucket_name=GCP_BUCKET_NAME) -> str:
        Determines and returns the path to the Google Cloud Storage (GCS) bucket folder
        based on the runtime environment (Google Cloud or local).

"""

import os
from datetime import datetime


from .config import Config


def get_unique_id() -> str:
    """
    Returns a unique identifier based on the current date and time.
    """
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def cmd_to_run_local_endpoint(cfg: Config) -> None:
    """
    Prints the commands to run the Docker container for the prediction service
    and make a POST request to the local endpoint."""

    path_service_account_json = f"{os.getcwd()}/service_account.json"

    print(f"""
First spin up the Docker container for the prediction service:

docker run \\
    -e AIP_HTTP_PORT=8081 \\
    -e AIP_STORAGE_URI="{cfg.BUCKET_URI}/{cfg.BUCKET_DIR_MODEL}" \\
    -e GOOGLE_APPLICATION_CREDENTIALS="/usr/app/service_account.json" \\
    -e AIP_HEALTH_ROUTE="/health" \\
    -e AIP_PREDICT_ROUTE="/predict" \\
    -p 8081:8081 \\
    -v {path_service_account_json}:/usr/app/service_account.json \\
    {cfg.DOCKER_IMAGE_URI_PRED}

Then make a POST request to the local endpoint:

curl -X POST \\
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \\
    -H "Content-Type: application/json" \\
    "http://localhost:8081/predict" \\
    -d "@prediction/request_test.json"
""")


def window_open(url):
    try:
        import IPython

    except ImportError:
        print("Cannot open {url} in a new window.")

    else:
        IPython.display.display(
            IPython.display.Javascript('window.open("{url}");'.format(url=url))
        )


def open_iam_permissions(project: str) -> None:
    link = f"https://console.cloud.google.com/iam-admin/iam?project={project}"

    window_open(link)
