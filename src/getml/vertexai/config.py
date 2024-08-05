"""
This module defines the Config class for managing configuration settings. The Config class utilizes
dataclass fields to store essential project information and provides several properties and methods
for easy access and manipulation of these configurations.

The Config class includes:
- Initialization from a dictionary of configuration settings.
- String representation for displaying current configuration.
- Properties for generating URIs for Google Cloud Storage, Docker images, and service accounts.
- Methods for saving the configuration to a YAML file and loading it from a YAML file.
- Utility methods for printing specific fields and generating console links for cloud resources.

Usage example:
    cfg = Config.load('path_to_config.yaml')
    print(cfg)
    cfg.save('new_config.yaml')
    cfg.print(['BUCKET_NAME', 'SERVICE_ACCOUNT_EMAIL'])
    cfg.print_links(['bucket', 'docker_repository'])
"""

import os
import sys
from dataclasses import dataclass
import yaml  # type: ignore
from getml.vertexai.utils_gcp import get_account_email

IS_WORKBENCH_ENV = "GOOGLE_VM_CONFIG_LOCK_FILE" in os.environ


@dataclass
class Config:
    GETML_PROJECT_NAME: str = os.environ.get("GETML_PROJECT_NAME", "")
    GCP_PROJECT_NAME: str = os.environ.get("GCP_PROJECT_NAME", "")
    REGION: str = os.environ.get("REGION", "")
    SERVICE_ACCOUNT_NAME: str = os.environ.get("SERVICE_ACCOUNT_NAME", "")
    BUCKET_NAME: str = os.environ.get("BUCKET_NAME", "")
    BUCKET_DIR_MODEL: str = os.environ.get("BUCKET_DIR_MODEL", "")
    BUCKET_DIR_DATASET: str = os.environ.get("BUCKET_DIR_DATASET", "")
    DOCKER_REPOSITORY: str = os.environ.get("DOCKER_REPOSITORY", "")

    def __init__(self, config: dict[str, str]):
        for key, value in config.items():
            setattr(self, key, value)

        if IS_WORKBENCH_ENV:
            self.SERVICE_ACCOUNT_NAME = get_account_email()

    def __repr__(self) -> str:
        """
        Returns a string representation of the current configuration, including all initialized fields and properties.

        Returns:
            str: A formatted string displaying the configuration fields and their values.
        """

        self._check_all_fields_set()

        props = {
            name: getattr(self, name)
            for name in dir(self)
            if isinstance(getattr(self.__class__, name, None), property)
        }
        fields = {
            key: value for key, value in self.__dict__.items() if isinstance(value, str)
        }
        all_fields = {**fields, **props}
        repr_str = "\n".join(f"{key:<28}{value!r}" for key, value in all_fields.items())
        return f"Current configuration\n=====================\n\n{repr_str}\n"

    @property
    def BUCKET_URI(self) -> str:
        return f"gs://{self.BUCKET_NAME}"

    @property
    def ARTIFACT_URI(self) -> str:
        return f"{self.BUCKET_URI}/{self.BUCKET_DIR_MODEL}"

    @property
    def SERVICE_ACCOUNT_EMAIL(self) -> str:
        if "gserviceaccount.com" in self.SERVICE_ACCOUNT_NAME:
            return self.SERVICE_ACCOUNT_NAME
        else:
            return f"{self.SERVICE_ACCOUNT_NAME}@{self.GCP_PROJECT_NAME}.iam.gserviceaccount.com"

    @property
    def DOCKER_IMAGE_URI_TRAIN(self) -> str:
        return f"{self.REGION}-docker.pkg.dev/{self.GCP_PROJECT_NAME}/{self.DOCKER_REPOSITORY}/{self.GETML_PROJECT_NAME.lower()}_train:latest"

    @property
    def DOCKER_IMAGE_URI_PRED(self) -> str:
        return f"{self.REGION}-docker.pkg.dev/{self.GCP_PROJECT_NAME}/{self.DOCKER_REPOSITORY}/{self.GETML_PROJECT_NAME.lower()}_pred:latest"

    @property
    def BUCKET_URI_DATASET(self) -> str:
        return f"gs://{self.BUCKET_NAME}/{self.BUCKET_DIR_DATASET}/{self.GETML_PROJECT_NAME}.csv"

    def save(self, filepath: str):
        fields = {
            key: value for key, value in self.__dict__.items() if isinstance(value, str)
        }
        with open(filepath, "w") as file:
            yaml.dump(fields, file, default_flow_style=False)

    @classmethod
    def load(cls, filepath: str) -> "Config":
        with open(filepath, "r") as file:
            config = yaml.safe_load(file)
        return cls(config)

    def _check_all_fields_set(self):
        """
        Checks if all configuration fields have been set with a value.
        If any field is not set, we exit.
        """
        keys_not_set = []

        for key, value in self.__dict__.items():
            if value is None or value == "":
                keys_not_set.append(key)

        if keys_not_set:
            sys.exit(
                f"Configuration field(s) '{keys_not_set}' not set. Please set all required fields."
            )

    def print(self, field_names: list[str]):
        """
        Prints the values of specified configuration fields in a formatted manner.

        Args:
            field_names (list[str]): A list of field names whose values are to be printed.
        """
        for field_name in field_names:
            value = getattr(self, field_name, None)
            if value is not None:
                print(f"{field_name + ':':<30}{value}")
        print("")

    def print_links(self, link_types: list[str], model_id: str = ""):
        """
        Prints console links for specified Google Cloud resources based on the provided link types.

        Args:
            link_types (list[str]): A list of link types to print. Supported types include 'bucket',
                                    'docker_repository', 'training_jobs', 'model_artifact',
                                    'experiments', 'image_for_predictions', 'model_registry',
                                    'platform_permissions' and 'deployed_model'.
            model_id (str, optional): The model ID to include in the "deployed_model" link.
        """
        links = {
            "bucket": f"https://console.cloud.google.com/storage/browser/{self.BUCKET_NAME}",
            "docker_repository": f"https://console.cloud.google.com/artifacts/docker/{self.GCP_PROJECT_NAME}/{self.REGION}/{self.DOCKER_REPOSITORY}",
            "training_jobs": f"https://console.cloud.google.com/vertex-ai/training/custom-jobs?project={self.GCP_PROJECT_NAME}",
            "model_artifact": f"https://console.cloud.google.com/storage/browser/{self.BUCKET_NAME}/{self.BUCKET_DIR_MODEL}",
            "experiments": f"https://console.cloud.google.com/vertex-ai/experiments/experiments?project={self.GCP_PROJECT_NAME}",
            "image_for_predictions": f"https://console.cloud.google.com/artifacts/docker/{self.GCP_PROJECT_NAME}/{self.REGION}/{self.DOCKER_REPOSITORY}/{self.GETML_PROJECT_NAME.lower()}_pred",
            "model_registry": f"https://console.cloud.google.com/vertex-ai/models?project={self.GCP_PROJECT_NAME}",
            "deployed_model": f"https://console.cloud.google.com/vertex-ai/models/locations/{self.REGION}/models/{model_id}/versions/1/deploy?project={self.GCP_PROJECT_NAME}",
            "iam_permissions": f"https://console.cloud.google.com/iam-admin/iam?project={self.GCP_PROJECT_NAME}",
        }

        for link_type in link_types:
            if link_type in links:
                print(
                    f"{link_type.replace('_', ' ').title() + ':':<30}{links[link_type]}"
                )
        print("")
