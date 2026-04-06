#!/usr/bin/env bash
# Upload a GitHub credential (PAT or SSH key) to AWS Secrets Manager.
#
# Usage:
#   upload_deploy_key.sh <secret-id> <credential-file-or-value> <region>
#
# If the second argument is a file path, the file contents are uploaded.
# Otherwise, the argument is treated as a literal string value.
#
# The secret must already exist in Secrets Manager (created by CDK).

set -eu

SECRET_ID="${1:?Usage: upload_deploy_key.sh <secret-id> <credential> <region>}"
CREDENTIAL="${2:?Usage: upload_deploy_key.sh <secret-id> <credential> <region>}"
AWS_REGION="${3:?Usage: upload_deploy_key.sh <secret-id> <credential> <region>}"

# If it's a file, read the contents; otherwise use as-is
if [ -f "$CREDENTIAL" ]; then
    SECRET_VALUE="$(cat "$CREDENTIAL")"
else
    SECRET_VALUE="$CREDENTIAL"
fi

echo "Uploading credential to Secrets Manager: $SECRET_ID"
aws secretsmanager put-secret-value \
    --secret-id "$SECRET_ID" \
    --secret-string "$SECRET_VALUE" \
    --region "$AWS_REGION"

echo "✓ Credential uploaded to: $SECRET_ID"
