#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

source .devcontainer/check_docker_rootless.sh

# Ensure PROJECT_NAME is set
if [ -z "$PROJECT_NAME" ]; then
  echo "PROJECT_NAME environment variable is not set."
  exit 1
fi

echo "Current project: $PROJECT_NAME"

cd "/workspaces/$PROJECT_NAME"

# Only execute if there is no "src" folder in the current dir
if [ ! -d "src" ]; then
  hatch new "$PROJECT_NAME"
  # Move all files and directories except pyproject.toml
  find "$PROJECT_NAME" -mindepth 1 -maxdepth 1 ! -name 'pyproject.toml' -exec mv -t . {} +
  rm -rf "$PROJECT_NAME"
fi

hatch env create

# Execute the passed command (default is /bin/bash)
exec "$@"