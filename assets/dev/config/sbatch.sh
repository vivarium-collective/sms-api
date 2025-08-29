#!/usr/bin/env bash

set -e
set -u
set -o pipefail
set -x

# load environment variables from .dev_env file in current directory
if [ -f .dev_env ]; then
    export $(grep -v '^#' .dev_env | xargs)
fi

ssh -i ${SLURM_SUBMIT_KEY_PATH} ${SLURM_SUBMIT_USER}@${SLURM_SUBMIT_HOST} sbatch $@
