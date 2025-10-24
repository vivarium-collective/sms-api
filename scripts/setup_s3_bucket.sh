#!/bin/bash
# Setup AWS S3 bucket for SMS API with proper permissions
# This script creates a bucket with SSE-S3 encryption (no KMS) to avoid permission issues

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AWS S3 Bucket Setup for SMS API ===${NC}\n"

# Step 1: Get current AWS identity
echo "Step 1: Checking AWS identity..."
IDENTITY=$(aws sts get-caller-identity)
ACCOUNT_ID=$(echo "$IDENTITY" | jq -r '.Account')
CURRENT_ARN=$(echo "$IDENTITY" | jq -r '.Arn')
CURRENT_USER=$(echo "$IDENTITY" | jq -r '.UserId')

echo "Account ID: $ACCOUNT_ID"
echo "Current ARN: $CURRENT_ARN"
echo "User ID: $CURRENT_USER"

# Extract SSO role if present
if [[ "$CURRENT_ARN" == *"assumed-role"* ]]; then
    SSO_ROLE_ARN="$CURRENT_ARN"
    echo -e "${GREEN}✅ Detected SSO role${NC}"
else
    SSO_ROLE_ARN=""
    echo -e "${YELLOW}⚠️  Not using SSO role${NC}"
fi

# Step 2: Configure bucket name and region
echo -e "\nStep 2: Configuring bucket name and region..."
DEFAULT_REGION="us-east-1"
DEFAULT_BUCKET="sms-api-storage-$(date +%Y%m%d)"

read -p "AWS Region [${DEFAULT_REGION}]: " AWS_REGION
AWS_REGION=${AWS_REGION:-$DEFAULT_REGION}

read -p "Bucket Name [${DEFAULT_BUCKET}]: " BUCKET_NAME
BUCKET_NAME=${BUCKET_NAME:-$DEFAULT_BUCKET}

echo "Region: $AWS_REGION"
echo "Bucket: $BUCKET_NAME"

# Step 3: Check if bucket already exists
echo -e "\nStep 3: Checking if bucket exists..."
if aws s3 ls "s3://${BUCKET_NAME}" 2>/dev/null; then
    echo -e "${RED}❌ Bucket already exists: ${BUCKET_NAME}${NC}"
    read -p "Do you want to use the existing bucket? (y/N): " USE_EXISTING
    if [[ "$USE_EXISTING" != "y" ]]; then
        echo "Exiting. Please choose a different bucket name."
        exit 1
    fi
    BUCKET_EXISTS=true
else
    BUCKET_EXISTS=false
fi

# Step 4: Create bucket if it doesn't exist
if [ "$BUCKET_EXISTS" = false ]; then
    echo -e "\nStep 4: Creating S3 bucket..."
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION"
    else
        aws s3api create-bucket \
            --bucket "$BUCKET_NAME" \
            --region "$AWS_REGION" \
            --create-bucket-configuration LocationConstraint="$AWS_REGION"
    fi
    echo -e "${GREEN}✅ Created bucket: ${BUCKET_NAME}${NC}"
else
    echo -e "${YELLOW}⚠️  Using existing bucket: ${BUCKET_NAME}${NC}"
fi

# Step 5: Configure SSE-S3 encryption (not KMS)
echo -e "\nStep 5: Configuring SSE-S3 encryption (no KMS)..."
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                },
                "BucketKeyEnabled": false
            }
        ]
    }'
echo -e "${GREEN}✅ Configured SSE-S3 encryption${NC}"

# Step 6: Enable versioning
echo -e "\nStep 6: Enabling versioning..."
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled
echo -e "${GREEN}✅ Enabled versioning${NC}"

# Step 7: Set bucket policy for SSO access (if applicable)
if [ -n "$SSO_ROLE_ARN" ]; then
    echo -e "\nStep 7: Setting bucket policy for SSO access..."

    cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowSSOUserFullAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "${SSO_ROLE_ARN}"
      },
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetObjectAttributes"
      ],
      "Resource": [
        "arn:aws:s3:::${BUCKET_NAME}",
        "arn:aws:s3:::${BUCKET_NAME}/*"
      ]
    }
  ]
}
EOF

    aws s3api put-bucket-policy \
        --bucket "$BUCKET_NAME" \
        --policy file:///tmp/bucket-policy.json

    rm /tmp/bucket-policy.json
    echo -e "${GREEN}✅ Set bucket policy for SSO access${NC}"
else
    echo -e "\n${YELLOW}Step 7: Skipping bucket policy (not using SSO)${NC}"
fi

# Step 8: Configure lifecycle policy for test files
echo -e "\nStep 8: Configuring lifecycle policy..."
cat > /tmp/lifecycle-policy.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteTestFilesAfter7Days",
      "Status": "Enabled",
      "Filter": {
        "Prefix": "test/"
      },
      "Expiration": {
        "Days": 7
      }
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
    --bucket "$BUCKET_NAME" \
    --lifecycle-configuration file:///tmp/lifecycle-policy.json

rm /tmp/lifecycle-policy.json
echo -e "${GREEN}✅ Configured lifecycle policy (test files deleted after 7 days)${NC}"

# Step 9: Test bucket access
echo -e "\nStep 9: Testing bucket access..."
TEST_FILE="/tmp/sms-api-test-$(date +%s).txt"
echo "Test content from $(date)" > "$TEST_FILE"

# Upload
echo "Testing upload..."
aws s3 cp "$TEST_FILE" "s3://${BUCKET_NAME}/test/setup-test.txt"
echo -e "${GREEN}✅ Upload successful${NC}"

# Download
echo "Testing download..."
aws s3 cp "s3://${BUCKET_NAME}/test/setup-test.txt" "${TEST_FILE}.downloaded"
echo -e "${GREEN}✅ Download successful${NC}"

# Verify content
if diff "$TEST_FILE" "${TEST_FILE}.downloaded" >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Content verification successful${NC}"
else
    echo -e "${RED}❌ Content mismatch!${NC}"
    exit 1
fi

# Delete
echo "Testing delete..."
aws s3 rm "s3://${BUCKET_NAME}/test/setup-test.txt"
echo -e "${GREEN}✅ Delete successful${NC}"

# Cleanup local files
rm -f "$TEST_FILE" "${TEST_FILE}.downloaded"

# Step 10: Display configuration
echo -e "\n${GREEN}=== Setup Complete! ===${NC}\n"
echo "Add these to your .env file or environment:"
echo ""
echo "export STORAGE_S3_BUCKET=\"${BUCKET_NAME}\""
echo "export STORAGE_S3_REGION=\"${AWS_REGION}\""
echo ""
echo "Bucket URL: https://s3.console.aws.amazon.com/s3/buckets/${BUCKET_NAME}"
echo ""
echo -e "${GREEN}✅ All tests passed! Your S3 bucket is ready for use.${NC}"
