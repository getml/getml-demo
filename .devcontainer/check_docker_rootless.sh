#!/bin/bash

# Check if docker is installed
if ! command -v docker &> /dev/null; then
  exit 0
fi

echo "Verifying rootless Docker installation..."

# Check if "name=rootless" is in SecurityOptions
rootless=$(docker info --format '{{json .}}' | jq -r '.SecurityOptions | index("name=rootless")')

if [ "$rootless" != "null" ]; then
  is_rootless=true
else
  is_rootless=false
fi

if [ "$is_rootless" = false ]; then
  echo "===================================================================="
  echo "  Docker deamon is running as root! Please install rootless Docker. "
  echo "  See: https://docs.docker.com/engine/security/rootless/            "
  echo "===================================================================="
  exit 1
fi
