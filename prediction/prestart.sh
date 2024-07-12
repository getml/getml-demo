#!/bin/bash
export PORT=$AIP_HTTP_PORT

# Starting the getML engine before starting the FastAPI server / gunicorn workers
python3 getml_engine.py