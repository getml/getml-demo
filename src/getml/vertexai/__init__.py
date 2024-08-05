__version__ = "0.1.0"

# Expose some classes and functions to the package's top level
from getml.vertexai.config import Config
from getml.vertexai.utils import (
    get_unique_id,
    cmd_to_run_local_endpoint,
    open_iam_permissions,
)
from getml.vertexai.utils_gcp import create_vertex_dataset_tabular
from getml.vertexai.request_data import (
    create_test_request,
    load_json_from_file,
)

__all__ = [
    "Config",
    "get_unique_id",
    "cmd_to_run_local_endpoint",
    "create_vertex_dataset_tabular",
    "create_test_request",
    "load_json_from_file",
    "open_iam_permissions",
]
