#!/usr/bin/env bash

set -eu  # Exit on error

# Get the directory where this script is located and calculate repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../" && pwd)"

# Set paths relative to the repository root
NAMESPACE=sms-api-eks
AWS_REGION=us-east-1
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

# call sealed_secret_shared.sh <namespace> <db_password> <jms_password> <mongo_user> <mongo_pswd>
echo "Generating shared secrets..."
${SCRIPTS_DIR}/sealed_secret_shared.sh --controller-name sealed-secrets --controller-namespace kube-system ${NAMESPACE} ${POSTGRES_USER} ${POSTGRES_PASSWORD} ${POSTGRES_DATABASE} ${POSTGRES_HOST} ${POSTGRES_PORT} > ${SECRETS_DIR}/secret-shared.yaml
cp ${SECRETS_DIR}/secret-shared.yaml ${MIGRATION_DIR}/secret-shared.yaml
echo "✓ secret-shared.yaml generated"

# call sealed_secret_ghcr.sh <namespace> <github_user> <github_user_email> <github_token>
echo "Generating GHCR secrets..."
${SCRIPTS_DIR}/sealed_secret_ghcr.sh --controller-name sealed-secrets --controller-namespace kube-system ${NAMESPACE} ${GH_USER_NAME} ${GH_USER_EMAIL} ${GH_PAT} > ${SECRETS_DIR}/secret-ghcr.yaml
cp ${SECRETS_DIR}/secret-ghcr.yaml ${MIGRATION_DIR}/secret-ghcr.yaml
echo "✓ secret-ghcr.yaml generated"

# call sealed_secret_ssh.sh <namespace> <priv_key_file> <pub_key_file>
echo "Generating SSH secrets..."
${SCRIPTS_DIR}/sealed_secret_ssh.sh --controller-name sealed-secrets --controller-namespace kube-system ${NAMESPACE} ${SSH_PRIV_KEY_FILE} ${SSH_PUB_KEY_FILE} > ${SECRETS_DIR}/secret-ssh.yaml
# cp ${SECRETS_DIR}/secret-ssh.yaml ${MIGRATION_DIR}/secret-ssh.yaml
echo "✓ secret-ssh.yaml generated"

echo ""
echo "=== Updating FSx Persistent Volume Configuration ==="

# Get FSx file system details
echo "Retrieving FSx file system details..."
FSX_INFO=$(aws fsx describe-file-systems \
  --region $AWS_REGION \
  --query 'FileSystems[?FileSystemType==`LUSTRE`] | [0].{Id:FileSystemId,DNS:DNSName,Mount:LustreConfiguration.MountName,ENIs:NetworkInterfaceIds}' \
  --output json)

FSX_ID=$(echo "$FSX_INFO" | jq -r '.Id')
FSX_DNS=$(echo "$FSX_INFO" | jq -r '.DNS')
FSX_MOUNT=$(echo "$FSX_INFO" | jq -r '.Mount')
FSX_ENI=$(echo "$FSX_INFO" | jq -r '.ENIs[0]')

if [ -z "$FSX_ID" ] || [ "$FSX_ID" == "null" ]; then
    echo "ERROR: Failed to retrieve FSx file system ID"
    exit 1
fi

# Get the IP address from the first network interface (Lustre requires IP, not DNS)
echo "Retrieving FSx network interface IP..."
FSX_IP=$(aws ec2 describe-network-interfaces \
  --region $AWS_REGION \
  --network-interface-ids "$FSX_ENI" \
  --query 'NetworkInterfaces[0].PrivateIpAddress' \
  --output text)

if [ -z "$FSX_IP" ] || [ "$FSX_IP" == "None" ]; then
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

# Get ElastiCache Redis endpoint
echo "Retrieving ElastiCache Redis endpoint..."
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
  --region $AWS_REGION \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' \
  --output text)

if [ -z "$REDIS_ENDPOINT" ] || [ "$REDIS_ENDPOINT" == "None" ]; then
    echo "ERROR: Failed to retrieve ElastiCache Redis endpoint"
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
echo "=== All secrets, ConfigMaps, and FSx configuration files generated successfully! ==="
