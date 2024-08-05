"""
This module contains utility functions and methods to interact with Google AI Platform and manage local prediction services using Docker.
It provides functionalities to generate unique identifiers, run shell commands, determine the Docker daemon path,
and open IAM permissions page for Google Cloud projects.

Functions:
    get_unique_id() -> str:
        Generates a unique identifier based on the current date and time.

    cmd_to_run_local_endpoint(cfg: Config) -> None:
        Prints the commands to run the Docker container for the prediction service
        and make a POST request to the local endpoint.

    open_iam_permissions(project: str) -> None:
        Opens the IAM permissions page for the specified Google Cloud project in a new browser window.

    run_shell_cmd(cmd: list[str]) -> str:
        Runs a command in the shell and returns the output. Prints an error message if the command fails.

    get_docker_daemon_path() -> str:
        Determines and returns the path to the Docker daemon.
"""

import os
import json
from typing import TYPE_CHECKING
import subprocess
from datetime import datetime

if TYPE_CHECKING:
    from getml.vertexai import Config


def get_unique_id() -> str:
    """
    Returns a unique identifier based on the current date and time.
    """
    return datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def cmd_to_run_local_endpoint(cfg: "Config") -> None:
    """
    Prints the commands to run the Docker container for the prediction service
    and make a POST request to the local endpoint.

    Args:
        cfg (Config): The configuration object containing details such as
                      BUCKET_URI, BUCKET_DIR_MODEL, DOCKER_IMAGE_URI_PRED, etc.
    """

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


def open_iam_permissions(project: str) -> None:
    """
    Opens the IAM permissions page for the specified Google Cloud project in a new browser window.

    Args:
        project (str): The Google Cloud project ID.
    """

    url = f"https://console.cloud.google.com/iam-admin/iam?project={project}"

    try:
        import IPython  # type: ignore

    except ImportError:
        print("Cannot open {url} in a new window.")

    else:
        IPython.display.display(
            IPython.display.Javascript('window.open("{url}");'.format(url=url))
        )


def run_shell_cmd(cmd: list[str]) -> str:
    """
    Runs a command in the shell.

    Args:
        cmd (list[str]): The command to run.

    Example:
        run_cmd(["ls", "-l"])

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code.
    """

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return ""
    else:
        return result.stdout.strip()


def get_docker_daemon_path() -> str:
    """
    Returns:
        str: The path to the Docker daemon.
    """

    deamon_path = ""
    docker_context = run_shell_cmd(["docker", "context", "ls", "--format", "json"])

    for context in docker_context.strip().split("\n"):
        context_json = json.loads(context)
        if context_json.get("Current", False):
            deamon_path = context_json.get("DockerEndpoint", "")
            break

    return deamon_path
