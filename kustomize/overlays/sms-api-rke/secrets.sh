#!/usr/bin/env bash

set -eu  # Exit on error

# Get the directory where this script is located and calculate repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../" && pwd)"

# Set paths relative to the repository root
NAMESPACE=sms-api-rke
SCRIPTS_DIR="${REPO_ROOT}/kustomize/scripts"
SECRETS_DIR="${REPO_ROOT}/kustomize/overlays/${NAMESPACE}"
MIGRATION_DIR="${REPO_ROOT}/kustomize/overlays/${NAMESPACE}-db-migration"

# Sealed secrets controller configuration (on-premise RKE cluster)
SEALED_SECRETS_CONTROLLER_NAME=sealed-secrets-controller
SEALED_SECRETS_CONTROLLER_NAMESPACE=kube-system

# Load secrets from data file (not committed to git)
SECRETS_DATA_FILE="${SECRETS_DIR}/secrets.dat"
if [ ! -f "$SECRETS_DATA_FILE" ]; then
    echo "ERROR: Secrets data file not found: $SECRETS_DATA_FILE"
    echo "Please create it from secrets.dat.template"
    echo "  cp ${SECRETS_DIR}/secrets.dat.template ${SECRETS_DIR}/secrets.dat"
    echo "  # Then edit secrets.dat with your actual values"
    exit 1
fi

echo "Loading secrets from: $SECRETS_DATA_FILE"
source "$SECRETS_DATA_FILE"

# Generate sealed secrets
echo ""
echo "=== Generating Sealed Secrets ==="

# call sealed_secret_shared.sh <namespace> <db_user> <db_password> <db_name> <db_host> <db_port>
echo "Generating shared secrets..."
${SCRIPTS_DIR}/sealed_secret_shared.sh \
    --controller-name ${SEALED_SECRETS_CONTROLLER_NAME} \
    --controller-namespace ${SEALED_SECRETS_CONTROLLER_NAMESPACE} \
    ${NAMESPACE} ${POSTGRES_USER} ${POSTGRES_PASSWORD} ${POSTGRES_DATABASE} ${POSTGRES_HOST} ${POSTGRES_PORT} \
    > ${SECRETS_DIR}/secret-shared.yaml
cp ${SECRETS_DIR}/secret-shared.yaml ${MIGRATION_DIR}/secret-shared.yaml
echo "✓ secret-shared.yaml generated"

# call sealed_secret_ghcr.sh <namespace> <github_user> <github_user_email> <github_token>
echo "Generating GHCR secrets..."
${SCRIPTS_DIR}/sealed_secret_ghcr.sh \
    --controller-name ${SEALED_SECRETS_CONTROLLER_NAME} \
    --controller-namespace ${SEALED_SECRETS_CONTROLLER_NAMESPACE} \
    ${NAMESPACE} ${GH_USER_NAME} ${GH_USER_EMAIL} ${GH_PAT} \
    > ${SECRETS_DIR}/secret-ghcr.yaml
cp ${SECRETS_DIR}/secret-ghcr.yaml ${MIGRATION_DIR}/secret-ghcr.yaml
echo "✓ secret-ghcr.yaml generated"

# call sealed_secret_ssh.sh <namespace> <priv_key_file> <pub_key_file>
echo "Generating SSH secrets..."
${SCRIPTS_DIR}/sealed_secret_ssh.sh \
    --controller-name ${SEALED_SECRETS_CONTROLLER_NAME} \
    --controller-namespace ${SEALED_SECRETS_CONTROLLER_NAMESPACE} \
    ${NAMESPACE} ${SSH_PRIV_KEY_FILE} ${SSH_PUB_KEY_FILE} \
    > ${SECRETS_DIR}/secret-ssh.yaml
# cp ${SECRETS_DIR}/secret-ssh.yaml ${MIGRATION_DIR}/secret-ssh.yaml
echo "✓ secret-ssh.yaml generated"

echo ""
echo "=== All sealed secrets generated successfully! ==="
