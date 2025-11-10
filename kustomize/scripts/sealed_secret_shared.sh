#!/usr/bin/env bash

set -u

# This script is used to create a sealed secret for the gcs storage
# this script should take 3 arguments as input:
#   namespace
#   mongodb_uri
#   and an optional --cert <filename.pem> argument to specify the certificate file for kubeseal
# Example: ./sealed_secret_shared.sh [--cert <filename.pem>] <namespace> <mongodb_uri> <storage_gcs_credentials_file> > output.yaml

# note that for GKE, the cert file is needed and can be extracted by running:
# kubeseal --fetch-cert > filename.pem
# or
# kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
#     | grep tls.crt | awk '{print $2}' | base64 --decode > filename.pem

# Initialize variables
CERT_ARG=""
CONTROLLER_NAME="sealed-secrets-controller"

# Parse optional arguments
while [[ "$1" == --* ]]; do
  case "$1" in
    --cert)
      CERT_ARG="$2"
      shift 2
      ;;
    --controller-name)
      CONTROLLER_NAME="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate the number of positional arguments
if [ "$#" -ne 6 ]; then
    echo "Illegal number of parameters"
    echo "Usage: ./sealed_secret_shared.sh [--cert <filename.pem>] <namespace> <postgres_user> <postgres_password> <postgres_database> <postgres_host> <postgres_port>"
    exit 1
fi

SECRET_NAME="shared-secrets"
NAMESPACE=$1
POSTGRES_USER=$2
POSTGRES_PASSWORD=$3
POSTGRES_DATABASE=$4
POSTGRES_HOST=$5
POSTGRES_PORT=$6

# construct a postgres URI
POSTGRES_URI="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DATABASE}"

# Create the generic secret and seal it
kubectl create secret generic ${SECRET_NAME} --dry-run=client \
      --from-literal=postgres-user="${POSTGRES_USER}" \
      --from-literal=postgres-password="${POSTGRES_PASSWORD}" \
      --from-literal=postgres-database="${POSTGRES_DATABASE}" \
      --from-literal=postgres-host="${POSTGRES_HOST}" \
      --from-literal=postgres-port="${POSTGRES_PORT}" \
      --from-literal=postgres-uri="${POSTGRES_URI}" \
      --namespace="${NAMESPACE}" -o yaml | kubeseal --controller-name=${CONTROLLER_NAME} --format yaml ${CERT_ARG:+--cert=$CERT_ARG}
