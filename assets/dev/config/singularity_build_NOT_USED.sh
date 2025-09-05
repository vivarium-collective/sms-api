#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <local_singularity_def> <local_singularity_image>"
    exit 1
fi

LOCAL_DEF="$1"
LOCAL_IMAGE="$2"

REMOTE_HOST="${SLURM_SUBMIT_HOST:-mantis-039}"
REMOTE_USER="${SLURM_SUBMIT_USER:-$USER}"
REMOTE_DEF="/tmp/$(basename "$LOCAL_DEF").$$.def"
REMOTE_IMAGE="/tmp/$(basename "$LOCAL_IMAGE").$$.sif"

# Upload the definition file
scp "$LOCAL_DEF" "${REMOTE_USER}@${REMOTE_HOST}:$REMOTE_DEF"

# Build the singularity image remotely
ssh "${REMOTE_USER}@${REMOTE_HOST}" \
    "singularity build --ignore-fakeroot-command --force '$REMOTE_IMAGE' '$REMOTE_DEF'"

# Download the built image to the local path
scp "${REMOTE_USER}@${REMOTE_HOST}:$REMOTE_IMAGE" "$LOCAL_IMAGE"

# Clean up remote files
ssh "${REMOTE_USER}@${REMOTE_HOST}" "rm -f '$REMOTE_DEF' '$REMOTE_IMAGE'"