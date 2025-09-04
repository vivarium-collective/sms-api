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

echo "building and pushing images for version ${version}"

for service in api; do
  tag="${version}"
  dockerfile="${ROOT_DIR}/Dockerfile-${service}"
  image_name="ghcr.io/vivarium-collective/sms-${service}:${tag}"

  if [[ ! -f "$dockerfile" ]]; then
    echo "ERROR: Dockerfile not found: $dockerfile"
    exit 1
  fi

  echo "Building $image_name using $dockerfile"
  docker buildx build \
    --platform=linux/amd64 \
    -f "${dockerfile}" \
    --tag "${image_name}" \
    --push \
    "${ROOT_DIR}" \
    || { echo "Failed to build ${service}"; exit 1; }

  echo "Built and pushed service ${service} version ${version}"
done
