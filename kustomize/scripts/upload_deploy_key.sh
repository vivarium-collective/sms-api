#!/usr/bin/env bash
# Upload a GitHub SSH deploy key to AWS Secrets Manager.
#
# Usage: upload_deploy_key.sh <secret-id> <key-file> <region>
#
# The secret must already exist in Secrets Manager (created by CDK).
# This script populates it with the contents of the SSH private key file.

set -eu

SECRET_ID="${1:?Usage: upload_deploy_key.sh <secret-id> <key-file> <region>}"
KEY_FILE="${2:?Usage: upload_deploy_key.sh <secret-id> <key-file> <region>}"
AWS_REGION="${3:?Usage: upload_deploy_key.sh <secret-id> <key-file> <region>}"

if [ ! -f "$KEY_FILE" ]; then
    echo "ERROR: Key file not found: $KEY_FILE"
    exit 1
fi

echo "Uploading deploy key to Secrets Manager..."
aws secretsmanager put-secret-value \
    --secret-id "$SECRET_ID" \
    --secret-string "$(cat "$KEY_FILE")" \
    --region "$AWS_REGION"

echo "✓ Deploy key uploaded to: $SECRET_ID"
