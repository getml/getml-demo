"""
This module provides utility functions for managing and using getML models with Google AI Platform.
It includes functionalities for running the getML engine, creating star schemas, converting data to JSON,
and loading configuration files.

Functions:
    _run_getml_engine(project: str) -> None:
        Launches the getML engine and sets the project.

    get_star_schema_testset(project: str) -> getml.data.StarSchema:
        Loads the Loans dataset and creates a star schema of the test set.

    convert_starschema_to_json(star_schema: getml.data.StarSchema, save_to_path: str = "./prediction/request_test.json", limit: int = 10) -> str:
        Converts and serializes the `population` table of the `star_schema.test` data to JSON format.

    load_json_from_file(file_path: str = "./prediction/request_test.json") -> str:
        Loads JSON data from a specified file.

    create_test_request(save_to_path: str = "./prediction/request_test.json") -> str:
        Creates a test request JSON file from the star schema test set and saves it to a specified path.
"""

import json
import getml
from getml.vertexai import Config


def get_star_schema_testset(project: str) -> getml.data.StarSchema:
    """
    Load Loans dataset and create a star schema of the test set.

    Args:
        project (str): The name of the getML project.

    Returns:
        StarSchema object that contains the population and peripheral tables.
    """

    # Launch getML engine
    getml.engine.launch(allow_remote_ips=True)
    getml.engine.set_project(project)

    # Load data
    population_train, population_test, order, trans, meta = getml.datasets.load_loans(
        roles=True, units=True
    )

    # Define Data Model
    star_schema = getml.data.StarSchema(
        train=population_train, test=population_test, alias="population"
    )

    # Join tables
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

    return star_schema.test


def convert_starschema_to_json(
    star_schema: getml.data.StarSchema,
    save_to_path: str = "./prediction/request_test.json",
    limit: int = 10,
) -> str:
    """
    Convert and serialize the `population` table of the `star_schema.test` data to JSON format.

    Args:
        star_schema (getml.data.StarSchema): The star schema object containing the test data.
        save_to_path (str): The path to save the request JSON file.
        limit (int): The number of rows to include in the JSON data.

    Returns:
        str: The request JSON data (serialized).
    """
    data_test_request = star_schema.population.to_arrow()[:limit].to_pydict()

    request_test_json = json.dumps({"instances": [data_test_request]}, default=str)

    # Write the JSON data to a file
    with open(save_to_path, "w") as file:
        file.write(request_test_json)

    return request_test_json


def load_json_from_file(file_path: str = "./prediction/request_test.json") -> str:
    with open(file_path, "r") as file:
        data = file.read()
    return data


def create_test_request(save_to_path: str = "./prediction/request_test.json") -> str:
    """
    Creates a test request JSON file from the star schema test set and saves it to a specified path.

    Args:
        save_to_path (str): The path to save the request JSON file.

    Returns:
        str: The request JSON data (serialized).
    """
    cfg = Config.load("config.yaml")

    star_schema_testset = get_star_schema_testset(cfg.GETML_PROJECT_NAME)
    request_json = convert_starschema_to_json(
        star_schema_testset, save_to_path=save_to_path
    )

    print(
        f"Test request data created successfully! \n Path: {save_to_path} \n Content: {request_json}"
    )
    return request_json
