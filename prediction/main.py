"""
This module sets up a FastAPI application to provide binary classification predictions using a getML pipeline.

It performs the following tasks:
- Loads configuration settings from "config.yaml".
- Initializes a PredictorClassificationBinary instance.
- Defines FastAPI endpoints for health checks and prediction requests.

FastAPI Endpoints:
- /health: Verifies the service is running.
- /predict: Handles prediction requests, processes input data, makes predictions, and returns results.
"""

import os
import logging
import numpy as np
from fastapi import FastAPI, Request

import getml

from getml.vertexai.config import Config

cfg = Config.load("config.yaml")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictorClassificationBinary:
    """
    This predictor class designed for binary classification predictions using a getML pipeline. It integrates
    with FastAPI to provide a web service for health checks and prediction requests.

    Key functionalities include:
    - Initialization and loading of the latest getML pipeline.
    - Preprocessing of input data to match the expected format of the getML model.
    - Loading a specific getML project.
    - Making predictions using the getML pipeline and the preprocessed input data.
    - Postprocessing prediction results into a JSON-compatible format.

    Attributes:
        pipe (getml.Pipeline): The latest pipeline from the getML project.

    Methods:
        __init__(): Initializes the PredictorClassificationBinary and loads the latest pipeline.
        _get_latest_pipeline(): Retrieves and logs the latest pipeline from the getML project.
        preprocess(prediction_input: dict) -> getml.DataFrame: Preprocesses input data for prediction.
        load(project: str): Loads a specified getML project.
        predict(instances: getml.DataFrame) -> np.ndarray: Predicts outcomes using the preprocessed data.
        postprocess(prediction_results: np.ndarray) -> dict: Converts prediction results to a JSON-compatible format.

    Usage example:
        predictor = PredictorClassificationBinary()
        predictor.load(project=cfg.GETML_PROJECT_NAME)
    """

    def __init__(self):
        self.pipe = self._get_latest_pipeline()

    def _get_latest_pipeline(self):
        if not getml.project.pipelines:
            raise ValueError("No pipelines found in the getML project.")

        pipeline = getml.project.pipelines[-1]
        logger.info(f"Loaded pipeline {pipeline.name}")
        return pipeline

    def preprocess(self, prediction_input: dict) -> getml.DataFrame:
        getml_roles = self.pipe.data_model.population.roles
        return getml.DataFrame.from_dict(
            data=prediction_input["instances"][0], name="Dataset", roles=getml_roles
        )

    def load(self, project: str) -> None:
        getml.engine.set_project(project)

    def predict(self, instances: getml.DataFrame) -> np.ndarray:
        getml_peripheral_names = [p.name for p in self.pipe.peripheral]
        getml_peripherials = {
            df.name: df
            for df in getml.project.data_frames
            if df.name in getml_peripheral_names
        }
        return self.pipe.predict(
            population_table=instances, peripheral_tables=getml_peripherials
        )

    def postprocess(self, prediction_results: np.ndarray) -> dict:
        return {"predictions": prediction_results.tolist()}


predictor = PredictorClassificationBinary()
predictor.load(project=cfg.GETML_PROJECT_NAME)

app = FastAPI()


# Define routes
@app.get(os.environ["AIP_HEALTH_ROUTE"], status_code=200)
def health():
    return {}


@app.post(os.environ["AIP_PREDICT_ROUTE"])
async def predict(request: Request):
    body = await request.json()
    preprocessed_data = predictor.preprocess(body)
    prediction_results = predictor.predict(preprocessed_data)
    response = predictor.postprocess(prediction_results)

    return response
