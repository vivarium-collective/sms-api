#!/usr/bin/env bash

kubectl apply -k kustomize/cluster
if [ $? -ne 0 ]; then
  echo "Error applying kustomize configuration. Please check your setup."
  exit 1
fi
