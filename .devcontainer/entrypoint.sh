#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e
# Change to the application directory
cd /workspaces/playbooks

# Create the hatch environment
hatch env create
# Execute the passed command (default is /bin/bash)
exec "$@"
