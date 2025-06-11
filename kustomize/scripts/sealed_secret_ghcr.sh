#!/usr/bin/env bash

# This script is used to create a sealed secret for the ghcr.io credentials
# this script should take 3 arguments as input: namespace, github username, github user email, and github token
# and an optional --cert <filename.pem> argument to specify the certificate file for kubeseal
# Example: ./sealed_secret_ghcr.sh remote GH_USERNAME GH_USER_EMAIL GH_PAT [--cert filename.pem] > output.yaml

# note that for GKE, the cert file is needed and can be extracted by running:
# kubeseal --fetch-cert > filename.pem
# or
# kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
#     | grep tls.crt | awk '{print $2}' | base64 --decode > filename.pem

# Initialize variables
CERT_ARG=""

# Parse optional arguments
while [[ "$1" == --* ]]; do
  case "$1" in
    --cert)
      CERT_ARG="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate the number of positional arguments
if [ "$#" -ne 4 ]; then
    echo "Illegal number of parameters"
    echo "Usage: ./sealed_secret_ghcr.sh  [--cert <filename.pem>] <namespace> <github_user> <github_user_email> <github_token>"
    exit 1
fi

SECRET_NAME="ghcr-secret"
SERVER="ghcr.io"
NAMESPACE=$1
USERNAME=$2
EMAIL=$3
PASSWORD=$4

# Create the docker-registry secret and seal it
kubectl create secret docker-registry ${SECRET_NAME} --dry-run=client \
      --docker-server="${SERVER}" \
      --docker-username="${USERNAME}" \
      --docker-email="${EMAIL}" \
      --docker-password="${PASSWORD}" \
      --namespace="${NAMESPACE}" -o yaml | kubeseal --format yaml ${CERT_ARG:+--cert=$CERT_ARG}
