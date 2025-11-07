#!/usr/bin/env bash

kubectl apply -k kustomize/cluster
if [ $? -ne 0 ]; then
  echo "Error applying kustomize configuration. Please check your setup."
  exit 1
fi

kubectl wait --for=condition=complete job/alembic-migrate
if [ $? -ne 0 ]; then
  echo "Error waiting for alembic-migrate job to complete. Please check the job status."
  exit 1
fi
