#!/usr/bin/env bash

# This script is used to create a sealed secret for the vcell ssh key used to interact with Slurm for HPC jobs.
# this script should take 3 arguments as input:
#   namespace
#   priv_key_file
#   pub_key_file
#   and an optional --cert <filename.pem> argument to specify the certificate file for kubeseal
#
#   and outputs a sealed secret to stdout
# Example: ./sealed_secret_ssh.sh [--cert <filename.pem>] <namespace> /path/to/vcell_rsa /path/to/vcell_rsa.pub > output.yaml

# note that for GKE and AWS GovCloud, the cert file is needed and can be extracted by running:
# kubeseal --fetch-cert > filename.pem
# or
# kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
#     | grep tls.crt | awk '{print $2}' | base64 --decode > filename.pem

# Initialize variables
CERT_ARG=""
CONTROLLER_NAME="sealed-secrets-controller"
CONTROLLER_NAMESPACE="sealed-secrets"

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
    --controller-namespace)
      CONTROLLER_NAMESPACE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# validate the number of arguments
if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters"
    echo "Usage: ./sealed_secret_ssh.sh [--cert <filename.pem>] <namespace> <priv_key_file> <pub_key_file>"
    exit 1
fi

SECRET_NAME="ssh-secret"
NAMESPACE=$1
PRIV_KEY_FILE=$2
PUB_KEY_FILE=$3

kubectl create secret generic ${SECRET_NAME} --dry-run=client \
      --from-file=ssh-privatekey="${PRIV_KEY_FILE}" \
      --from-file=ssh-publickey="${PUB_KEY_FILE}" \
      --namespace="${NAMESPACE}" -o yaml | kubeseal --controller-name=${CONTROLLER_NAME} --controller-namespace=${CONTROLLER_NAMESPACE} --format yaml ${CERT_ARG:+--cert=$CERT_ARG}
