#!/bin/bash
set -euo pipefail

# Resolve root of repo after GitHub Actions checkout
ROOT_DIR="${GITHUB_WORKSPACE}"

# Make sure version.py exists
VERSION_FILE="${ROOT_DIR}/sms_api/version.py"
if [[ ! -f "$VERSION_FILE" ]]; then
  echo "ERROR: version.py not found at $VERSION_FILE"
  exit 1
fi

# Extract version
declared_version=$(grep -oE '__version__ = \"[^\"]+\"' "$VERSION_FILE" | awk -F'"' '{print $2}')
version=${1:-${declared_version}}

echo "Building and pushing Singularity images for version ${version}"

for service in api; do
  tag="${version}"
  dockerfile="${ROOT_DIR}/Dockerfile-${service}"
  image_name="ghcr.io/vivarium-collective/sms-${service}:${tag}"
  sif_name="sms-${service}-${tag}.sif"

  if [[ ! -f "$dockerfile" ]]; then
    echo "ERROR: Dockerfile not found: $dockerfile"
    exit 1
  fi

  echo "Building Docker image $image_name"
  docker buildx build \
    --platform=linux/amd64 \
    -f "${dockerfile}" \
    --tag "${image_name}" \
    "${ROOT_DIR}"

  echo "Building Singularity image $sif_name from Docker image"
  apptainer build "${sif_name}" "docker-daemon:${image_name}"

  echo "Pushing Singularity image to ghcr.io"
  apptainer push "${sif_name}" "oras://${image_name}"

  echo "Built and pushed service ${service} version ${version} as Docker and Singularity images"
done