#!/usr/bin/env bash

set -eu  # Exit on error

# Get the directory where this script is located and calculate repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../" && pwd)"

# Set paths relative to the repository root
NAMESPACE=sms-api-stanford-test
AWS_REGION=us-gov-west-1
SCRIPTS_DIR="${REPO_ROOT}/kustomize/scripts"
SECRETS_DIR="${REPO_ROOT}/kustomize/overlays/${NAMESPACE}"
MIGRATION_DIR="${REPO_ROOT}/kustomize/overlays/${NAMESPACE}-db-migration"
CONFIG_DIR="${REPO_ROOT}/kustomize/config/${NAMESPACE}"

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

# Validate STACK_PREFIX is set
if [ -z "$STACK_PREFIX" ]; then
    echo "ERROR: STACK_PREFIX not set in $SECRETS_DATA_FILE"
    echo "Please add: STACK_PREFIX=\"your-stack-prefix\" (e.g., smscdk, smsvpctest)"
    exit 1
fi

echo "Stack prefix: $STACK_PREFIX"

# Helper function to get CloudFormation stack output
get_stack_output() {
    local stack_name="$1"
    local output_key="$2"
    aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$AWS_REGION" \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null
}

# Look up resources from CloudFormation stack outputs
echo ""
echo "=== Looking up resources from CloudFormation stacks ==="

# Get login node instance ID from login stack
LOGIN_NODE_INSTANCE_ID=$(get_stack_output "${STACK_PREFIX}-login" "LoginInstanceId")
if [ -z "$LOGIN_NODE_INSTANCE_ID" ] || [ "$LOGIN_NODE_INSTANCE_ID" = "None" ]; then
    echo "ERROR: Could not find LoginInstanceId from ${STACK_PREFIX}-login stack"
    exit 1
fi
echo "✓ Login node instance ID: $LOGIN_NODE_INSTANCE_ID"

# Get database secret ARN from shared stack
SECRET_ARN=$(get_stack_output "${STACK_PREFIX}-shared" "DbSecretArn")
if [ -z "$SECRET_ARN" ] || [ "$SECRET_ARN" = "None" ]; then
    echo "ERROR: Could not find DbSecretArn from ${STACK_PREFIX}-shared stack"
    exit 1
fi
echo "✓ Database secret ARN: $SECRET_ARN"

# Retrieve database credentials from AWS Secrets Manager
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id $SECRET_ARN --region $AWS_REGION --query SecretString --output text)

POSTGRES_USER=$(echo $SECRET_JSON | jq -r '.username')
POSTGRES_PASSWORD=$(echo $SECRET_JSON | jq -r '.password')
POSTGRES_HOST=$(echo $SECRET_JSON | jq -r '.host')
POSTGRES_PORT=$(echo $SECRET_JSON | jq -r '.port')
POSTGRES_DATABASE=postgres

# Function to generate SSH known_hosts ConfigMap
function generate_ssh_known_hosts_configmap() {
    local instance_id=$1
    local output_file=$2

    echo "Retrieving SSH host keys from login node instance: ${instance_id}..."

    # Send SSM command to retrieve SSH host keys
    local command_id=$(aws ssm send-command \
        --region $AWS_REGION \
        --instance-ids "${instance_id}" \
        --document-name "AWS-RunShellScript" \
        --parameters 'commands=["cd /etc/ssh && for f in ssh_host_*.pub; do echo -n \"login-node.pcs.internal \"; cat $f; done"]' \
        --query 'Command.CommandId' \
        --output text)

    # Wait for command to complete
    echo "Waiting for SSM command to complete..."
    sleep 3

    # Retrieve command output
    local host_keys=$(aws ssm get-command-invocation \
        --region $AWS_REGION \
        --command-id "${command_id}" \
        --instance-id "${instance_id}" \
        --query "StandardOutputContent" \
        --output text)

    if [ -z "$host_keys" ]; then
        echo "ERROR: Failed to retrieve SSH host keys"
        return 1
    fi

    # Generate ConfigMap YAML with proper indentation
    cat > "${output_file}" <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: ssh-known-hosts
data:
  known_hosts: |
$(echo "$host_keys" | sed 's/^/    /')
EOF

    echo "✓ SSH known_hosts ConfigMap generated: ${output_file}"
}

# Generate SSH known_hosts ConfigMap
echo ""
echo "=== Generating SSH Known Hosts ConfigMap ==="
generate_ssh_known_hosts_configmap "${LOGIN_NODE_INSTANCE_ID}" "${CONFIG_DIR}/ssh-known-hosts-configmap.yaml"

# Generate sealed secrets
echo ""
echo "=== Generating Sealed Secrets ==="

# Fetch sealed-secrets certificate from cluster (needed for AWS GovCloud)
echo "Fetching sealed-secrets certificate from cluster..."
CERT_FILE=$(mktemp)
kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o jsonpath='{.items[0].data.tls\.crt}' | base64 -d > "${CERT_FILE}"
echo "✓ Certificate saved to temporary file"

# Cleanup function to remove temp cert file
cleanup() {
    rm -f "${CERT_FILE}"
}
trap cleanup EXIT

# call sealed_secret_shared.sh <namespace> <db_password> <jms_password> <mongo_user> <mongo_pswd>
echo "Generating shared secrets..."
${SCRIPTS_DIR}/sealed_secret_shared.sh --cert "${CERT_FILE}" --controller-name sealed-secrets --controller-namespace kube-system ${NAMESPACE} ${POSTGRES_USER} ${POSTGRES_PASSWORD} ${POSTGRES_DATABASE} ${POSTGRES_HOST} ${POSTGRES_PORT} > ${SECRETS_DIR}/secret-shared.yaml
cp ${SECRETS_DIR}/secret-shared.yaml ${MIGRATION_DIR}/secret-shared.yaml
echo "✓ secret-shared.yaml generated"

# call sealed_secret_ghcr.sh <namespace> <github_user> <github_user_email> <github_token>
echo "Generating GHCR secrets..."
${SCRIPTS_DIR}/sealed_secret_ghcr.sh --cert "${CERT_FILE}" --controller-name sealed-secrets --controller-namespace kube-system ${NAMESPACE} ${GH_USER_NAME} ${GH_USER_EMAIL} ${GH_PAT} > ${SECRETS_DIR}/secret-ghcr.yaml
cp ${SECRETS_DIR}/secret-ghcr.yaml ${MIGRATION_DIR}/secret-ghcr.yaml
echo "✓ secret-ghcr.yaml generated"

# call sealed_secret_ssh.sh <namespace> <priv_key_file> <pub_key_file>
echo "Generating SSH secrets..."
${SCRIPTS_DIR}/sealed_secret_ssh.sh --cert "${CERT_FILE}" --controller-name sealed-secrets --controller-namespace kube-system ${NAMESPACE} ${SSH_PRIV_KEY_FILE} ${SSH_PUB_KEY_FILE} > ${SECRETS_DIR}/secret-ssh.yaml
# cp ${SECRETS_DIR}/secret-ssh.yaml ${MIGRATION_DIR}/secret-ssh.yaml
echo "✓ secret-ssh.yaml generated"

echo ""
echo "=== Updating FSx Persistent Volume Configuration ==="

# Get FSx file system details from CloudFormation stack outputs
echo "Retrieving FSx file system details from ${STACK_PREFIX}-shared stack..."
FSX_ID=$(get_stack_output "${STACK_PREFIX}-shared" "FsxFileSystemId")
FSX_DNS=$(get_stack_output "${STACK_PREFIX}-shared" "FsxDnsName")
FSX_MOUNT=$(get_stack_output "${STACK_PREFIX}-shared" "FsxMountName")

if [ -z "$FSX_ID" ] || [ "$FSX_ID" = "None" ]; then
    echo "ERROR: Could not find FsxFileSystemId from ${STACK_PREFIX}-shared stack"
    exit 1
fi

if [ -z "$FSX_MOUNT" ] || [ "$FSX_MOUNT" = "None" ]; then
    echo "ERROR: Could not find FsxMountName from ${STACK_PREFIX}-shared stack"
    exit 1
fi

# Get FSx IP address from the file system's network interface
echo "Retrieving FSx network interface IP..."
FSX_ENI=$(aws fsx describe-file-systems \
  --region $AWS_REGION \
  --file-system-ids "$FSX_ID" \
  --query 'FileSystems[0].NetworkInterfaceIds[0]' \
  --output text)

FSX_IP=$(aws ec2 describe-network-interfaces \
  --region $AWS_REGION \
  --network-interface-ids "$FSX_ENI" \
  --query 'NetworkInterfaces[0].PrivateIpAddress' \
  --output text)

if [ -z "$FSX_IP" ] || [ "$FSX_IP" = "None" ]; then
    echo "ERROR: Failed to retrieve FSx network interface IP"
    exit 1
fi

echo "✓ FSx file system ID: ${FSX_ID}"
echo "✓ FSx DNS name: ${FSX_DNS}"
echo "✓ FSx IP address: ${FSX_IP}"
echo "✓ FSx mount name: ${FSX_MOUNT}"

# Generate the FSx PV YAML file from template
FSX_PV_TEMPLATE="${SECRETS_DIR}/fsx-pcs-root-pv.yaml.template"
FSX_PV_FILE="${SECRETS_DIR}/fsx-pcs-root-pv.yaml"
echo "Generating FSx PersistentVolume YAML from template..."

# Generate YAML from template by replacing placeholders
sed \
  -e "s/\${FSX_ID}/${FSX_ID}/g" \
  -e "s/\${FSX_IP}/${FSX_IP}/g" \
  -e "s/\${FSX_MOUNT}/${FSX_MOUNT}/g" \
  "${FSX_PV_TEMPLATE}" > "${FSX_PV_FILE}"

echo "✓ FSx PersistentVolume YAML generated: ${FSX_PV_FILE}"

echo ""
echo "=== Updating Redis Configuration in shared.env ==="

# Get ElastiCache Redis endpoint from CloudFormation stack outputs
echo "Retrieving ElastiCache Redis endpoint from ${STACK_PREFIX}-shared stack..."
REDIS_ENDPOINT=$(get_stack_output "${STACK_PREFIX}-shared" "RedisEndpoint")

if [ -z "$REDIS_ENDPOINT" ] || [ "$REDIS_ENDPOINT" = "None" ]; then
    echo "ERROR: Could not find RedisEndpoint from ${STACK_PREFIX}-shared stack"
    exit 1
fi

echo "✓ Redis endpoint: ${REDIS_ENDPOINT}"

# Update shared.env with the Redis endpoint
SHARED_ENV_FILE="${CONFIG_DIR}/shared.env"
echo "Updating Redis hosts in ${SHARED_ENV_FILE}..."

sed -i.bak \
  -e "s|^REDIS_INTERNAL_HOST=.*|REDIS_INTERNAL_HOST=${REDIS_ENDPOINT}|" \
  -e "s|^REDIS_EXTERNAL_HOST=.*|REDIS_EXTERNAL_HOST=${REDIS_ENDPOINT}|" \
  "${SHARED_ENV_FILE}" && rm -f "${SHARED_ENV_FILE}.bak"

echo "✓ Redis configuration updated in shared.env"

echo ""
echo "=== Updating Target Group Bindings for Verified Access ==="

# Get Target Group ARNs from CDK stack outputs
echo "Retrieving Target Group ARNs from ${STACK_PREFIX}-internal-alb stack..."
API_TARGET_GROUP_ARN=$(get_stack_output "${STACK_PREFIX}-internal-alb" "ApiTargetGroupArn")
PTOOLS_TARGET_GROUP_ARN=$(get_stack_output "${STACK_PREFIX}-internal-alb" "PtoolsTargetGroupArn")

if [ -z "$API_TARGET_GROUP_ARN" ] || [ "$API_TARGET_GROUP_ARN" = "None" ]; then
    echo "ERROR: Could not find ApiTargetGroupArn from ${STACK_PREFIX}-internal-alb stack"
    exit 1
fi

if [ -z "$PTOOLS_TARGET_GROUP_ARN" ] || [ "$PTOOLS_TARGET_GROUP_ARN" = "None" ]; then
    echo "ERROR: Could not find PtoolsTargetGroupArn from ${STACK_PREFIX}-internal-alb stack"
    exit 1
fi

echo "✓ API Target Group ARN: ${API_TARGET_GROUP_ARN}"
echo "✓ Ptools Target Group ARN: ${PTOOLS_TARGET_GROUP_ARN}"

# Generate the TargetGroupBinding YAML from template
TGB_TEMPLATE="${SECRETS_DIR}/target-group-binding.yaml.template"
TGB_FILE="${SECRETS_DIR}/target-group-binding.yaml"
echo "Generating TargetGroupBinding YAML from template..."

sed \
  -e "s|\${API_TARGET_GROUP_ARN}|${API_TARGET_GROUP_ARN}|g" \
  -e "s|\${PTOOLS_TARGET_GROUP_ARN}|${PTOOLS_TARGET_GROUP_ARN}|g" \
  "${TGB_TEMPLATE}" > "${TGB_FILE}"

echo "✓ TargetGroupBinding YAML generated: ${TGB_FILE}"

echo ""
echo "=== Uploading GitHub PAT for DinD Builds to Secrets Manager ==="

# Get the git secret ARN from the build-batch stack
GIT_SECRET_ARN=$(get_stack_output "${STACK_PREFIX}-build-batch" "GitSecretArn")

if [ -z "$GIT_SECRET_ARN" ] || [ "$GIT_SECRET_ARN" = "None" ]; then
    echo "WARNING: Could not find GitSecretArn from ${STACK_PREFIX}-build-batch stack, skipping"
elif [ -z "${GITHUB_BUILD_PAT:-}" ]; then
    echo "WARNING: GITHUB_BUILD_PAT not set in secrets.dat, skipping"
else
    # Allow reusing the GH_PAT used for GHCR
    BUILD_PAT="${GITHUB_BUILD_PAT}"
    if [ "$BUILD_PAT" = "use_gh_pat" ]; then
        BUILD_PAT="${GH_PAT}"
    fi
    ${SCRIPTS_DIR}/upload_deploy_key.sh "$GIT_SECRET_ARN" "$BUILD_PAT" "$AWS_REGION"
fi

echo ""
echo "=== All secrets, ConfigMaps, and FSx configuration files generated successfully! ==="
