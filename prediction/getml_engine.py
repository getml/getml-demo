"""
This module is responsible for initializing the getML engine and loading the necessary model artifacts
for use by the FastAPI application. It is designed to be called before `main.py` to ensure that the engine is properly
initialized and the model is ready for making predictions.

The key functionalities of this module include:
- Loading the configuration settings from a YAML file.
- Launching the getML engine.
- Retrieving the model artifact from Google Cloud Storage (GCS).
- Loading the model artifact and associated data frames into the getML project.

This setup ensures that the FastAPI application has immediate access to the pre-loaded getML model and data frames,
and prevents race conditions that may occur when loading multiple workers in parallel.

Note:
- The environment variable `AIP_STORAGE_URI` is retrieved from the Vertex AI custom container environment and should be set to the GCS URI of the model artifact directory.
- The configuration file `config.yaml` must include the necessary settings for accessing the GCS bucket and model directories.
"""

import os
import getml

from getml.vertexai.utils_gcp import load_from_gcs
from getml.vertexai.config import Config

cfg = Config.load("config.yaml")

getml.engine.launch(launch_browser=False)

# Get the model artifact from GCS
artifacts_uri_full = f"{os.environ['AIP_STORAGE_URI']}/{cfg.GETML_PROJECT_NAME}.getml"
artifact_path_local = load_from_gcs(
    cfg, gcs_path=artifacts_uri_full, folder_name=cfg.BUCKET_DIR_MODEL
)

# Load the model artifact
getml.project.load(artifact_path_local)
getml.project.data_frames.load()
