#!/bin/bash
# Helper functions for working with S3-compatible storage (AWS S3, Qumulo, etc.)
# This script provides unified functions that work with different S3 providers
#
# Usage:
#   Set STORAGE_TYPE to "qumulo" or "aws" (default: "aws")
#   Set STORAGE_ENDPOINT_URL for non-AWS providers (e.g., Qumulo)
#   Set STORAGE_BUCKET for the bucket name
#   Set STORAGE_VERIFY_SSL to "false" to disable SSL verification (default: "true")
#
# Environment Variables:
#   STORAGE_TYPE: "qumulo" or "aws" (determines if special handling is needed)
#   STORAGE_ENDPOINT_URL: S3 endpoint URL (required for Qumulo, optional for AWS)
#   STORAGE_BUCKET: S3 bucket name
#   STORAGE_VERIFY_SSL: "true" or "false" (default: "true")
#   AWS_ACCESS_KEY_ID: AWS/Qumulo access key
#   AWS_SECRET_ACCESS_KEY: AWS/Qumulo secret key
#   AWS_DEFAULT_REGION: AWS region (default: "us-east-1")

# Function to get aws cli arguments based on storage type
_get_aws_args() {
    local args=""

    # Add endpoint URL if specified (for Qumulo or custom S3)
    if [ -n "$STORAGE_ENDPOINT_URL" ]; then
        args="$args --endpoint-url $STORAGE_ENDPOINT_URL"
    fi

    # Disable SSL verification if requested
    if [ "$STORAGE_VERIFY_SSL" = "false" ]; then
        args="$args --no-verify-ssl"
    fi

    echo "$args"
}

# Function to check if we need Qumulo-specific handling
_is_qumulo() {
    [ "$STORAGE_TYPE" = "qumulo" ]
}

# Download a file from S3-compatible storage
s3_download() {
    local key="$1"
    local file="$2"

    # Validate required environment variables
    if [ -z "$STORAGE_BUCKET" ]; then
        echo "Error: STORAGE_BUCKET not set" >&2
        return 1
    fi
    if [ -z "$AWS_ACCESS_KEY_ID" ]; then
        echo "Error: AWS_ACCESS_KEY_ID not set" >&2
        return 1
    fi
    if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        echo "Error: AWS_SECRET_ACCESS_KEY not set" >&2
        return 1
    fi

    local storage_label="${STORAGE_TYPE:-aws}"
    echo "Downloading from $storage_label S3: s3://${STORAGE_BUCKET}/${key} to '$file'"

    local aws_args=$(_get_aws_args)

    # Set Qumulo-specific environment variables if needed
    if _is_qumulo; then
        export AWS_REQUEST_CHECKSUM_CALCULATION=when_required
        export AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
    fi

    # shellcheck disable=SC2086
    if aws s3api get-object \
        $aws_args \
        --bucket "$STORAGE_BUCKET" \
        --key "$key" \
        "$file"; then
        echo "Download successful"
        return 0
    else
        echo "Error: Download failed" >&2
        return 1
    fi
}

# Upload a file to S3-compatible storage
# For Qumulo: automatically handles delete-before-upload to work around no-overwrite restriction
s3_upload() {
    local file="$1"
    local key="$2"

    # Validate required environment variables
    if [ -z "$STORAGE_BUCKET" ]; then
        echo "Error: STORAGE_BUCKET not set" >&2
        return 1
    fi
    if [ -z "$AWS_ACCESS_KEY_ID" ]; then
        echo "Error: AWS_ACCESS_KEY_ID not set" >&2
        return 1
    fi
    if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
        echo "Error: AWS_SECRET_ACCESS_KEY not set" >&2
        return 1
    fi

    # Check if file exists locally
    if [ ! -f "$file" ]; then
        echo "Error: Local file '$file' not found" >&2
        return 1
    fi

    local storage_label="${STORAGE_TYPE:-aws}"
    local aws_args=$(_get_aws_args)

    # Set Qumulo-specific environment variables if needed
    if _is_qumulo; then
        export AWS_REQUEST_CHECKSUM_CALCULATION=when_required
        export AWS_RESPONSE_CHECKSUM_VALIDATION=when_required
    fi

    # For Qumulo, check if object exists and delete it first (Qumulo doesn't allow overwrites)
    if _is_qumulo; then
        echo "Checking if object exists in $storage_label: s3://${STORAGE_BUCKET}/${key}"

        # shellcheck disable=SC2086
        if aws s3api head-object \
            $aws_args \
            --bucket "$STORAGE_BUCKET" \
            --key "$key" 2>/dev/null; then

            echo "Object exists, deleting before upload (Qumulo no-overwrite restriction)..."
            # shellcheck disable=SC2086
            if ! aws s3api delete-object \
                $aws_args \
                --bucket "$STORAGE_BUCKET" \
                --key "$key"; then
                echo "Error: Failed to delete existing object" >&2
                return 1
            fi
            echo "Existing object deleted"
        else
            echo "Object does not exist, proceeding with upload"
        fi
    fi

    # Upload the file
    echo "Uploading '$file' to $storage_label S3: s3://${STORAGE_BUCKET}/${key}"
    # shellcheck disable=SC2086
    if aws s3api put-object \
        $aws_args \
        --bucket "$STORAGE_BUCKET" \
        --key "$key" \
        --body "$file"; then
        echo "Upload successful"
        return 0
    else
        echo "Error: Upload failed" >&2
        return 1
    fi
}

# Export functions so they're available to subshells
export -f s3_download
export -f s3_upload
export -f _get_aws_args
export -f _is_qumulo
