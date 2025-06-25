#!/bin/bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# version is an optional argument, defaults to the version defined in sms_api/version.py'
#
# version.py is of form:
# __version__ = "0.1.0"
declared_version=$(grep -oE '__version__ = \"[^\"]+\"' "${ROOT_DIR}/sms_api/version.py" | awk -F'"' '{print $2}')
version=${1:-${declared_version}}

echo "building and pushing images for version ${version}"

# for architecture in amd64 arm64; do
for architecture in amd64; do

  for service in api; do

    tag="${architecture}_${version}"
    platform="linux/${architecture}"
    dockerfile="${ROOT_DIR}/Dockerfile-${service}"
    image_name="ghcr.io/biosimulations/sms-${service}:${tag}"

    docker build --platform=${platform} -f ${dockerfile} --tag ${image_name} "${ROOT_DIR}" \
      || { echo "Failed to build ${service} for platform ${platform}"; exit 1; }

    docker push ${image_name}  \
      || { echo "Failed to push ${service} for platform ${platform}"; exit 1; }

    echo "built and pushed service ${service} version ${version} for platform ${platform}"
  done
done
