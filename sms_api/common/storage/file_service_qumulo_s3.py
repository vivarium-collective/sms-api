import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError
from typing_extensions import override

from sms_api.common.storage.file_service import FileService, ListingItem
from sms_api.config import get_local_cache_dir, get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class FileServiceQumuloS3(FileService):
    """
    Qumulo S3-compatible object storage implementation of FileService.

    Qumulo supports S3-compatible API with path-style access instead of bucket-style.
    This implementation is optimized for Qumulo's filesystem-oriented S3 interface.

    Key differences from standard S3:
    - Uses path-style access (endpoint/path) instead of bucket.domain style
    - Paths map directly to Qumulo filesystem paths
    - Single "bucket" represents the Qumulo filesystem root

    Configuration (via Settings):
    - storage_qumulo_endpoint_url: Qumulo S3 endpoint (e.g., 'https://qumulo.example.com:8000')
    - storage_qumulo_access_key_id: Qumulo access key
    - storage_qumulo_secret_access_key: Qumulo secret key
    - storage_qumulo_bucket: Root bucket/path (often just the filesystem name)
    - storage_qumulo_verify_ssl: Whether to verify SSL certificates (default: True)
    """

    session: aioboto3.Session
    endpoint_url: str
    verify_ssl: bool
    config: Config

    def __init__(self) -> None:
        settings = get_settings()
        self.endpoint_url = settings.storage_qumulo_endpoint_url
        self.verify_ssl = settings.storage_qumulo_verify_ssl

        # Disable AWS checksums that Qumulo doesn't support
        # Set environment variables that control AWS SDK checksum behavior
        os.environ['AWS_REQUEST_CHECKSUM_CALCULATION'] = 'when_required'
        os.environ['AWS_RESPONSE_CHECKSUM_VALIDATION'] = 'when_required'

        # Create session with Qumulo credentials
        self.session = aioboto3.Session(
            aws_access_key_id=settings.storage_qumulo_access_key_id,
            aws_secret_access_key=settings.storage_qumulo_secret_access_key,
        )

        # Configure for Qumulo S3 compatibility
        # Force path-style addressing and disable payload signing
        # Qumulo doesn't support the newer AWS checksums (CRC64NVME, etc.)
        self.config = Config(
            s3={
                'addressing_style': 'path',
                'payload_signing_enabled': False,
            },
            signature_version='s3v4',
        )

        # For SSL verification, we need to pass it separately to the client
        # since Config doesn't support the 'verify' parameter

    def _get_client_kwargs(self) -> dict[str, Any]:
        """
        Get the kwargs for creating an S3 client.

        Returns a dict with properly typed arguments for aioboto3.Session.client().
        """
        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "endpoint_url": self.endpoint_url,
            "config": self.config,
            "region_name": "us-east-1",
        }
        if not self.verify_ssl:
            kwargs["verify"] = False
        return kwargs

    def _parse_qumulo_path(self, path: str) -> tuple[str, str]:
        """
        Parse path into bucket and key for Qumulo.

        Qumulo uses a single bucket representing the filesystem root,
        and keys are filesystem paths.

        Supports formats:
        - s3://bucket/path/to/file
        - qumulo://path/to/file
        - /path/to/file
        - path/to/file

        Returns:
            tuple: (bucket_name, key_path)
        """
        settings = get_settings()

        # Remove protocol prefixes
        clean_path = path.replace("s3://", "").replace("qumulo://", "")

        # If path starts with /, treat as absolute filesystem path
        if clean_path.startswith("/"):
            return settings.storage_qumulo_bucket, clean_path.lstrip("/")

        # If path contains bucket separator
        if "/" in clean_path:
            parts = clean_path.split("/", 1)
            # Check if first part looks like a bucket name
            # For Qumulo, typically use the configured bucket
            return settings.storage_qumulo_bucket, clean_path
        else:
            return settings.storage_qumulo_bucket, clean_path

    @override
    async def download_file(self, gcs_path: str, file_path: Optional[Path] = None) -> tuple[str, str]:
        """
        Download a file from Qumulo S3 to local filesystem.

        Note: Parameter name kept as 'gcs_path' for interface compatibility,
        but accepts Qumulo filesystem paths.
        """
        logger.info(f"Downloading Qumulo file: {gcs_path} to {file_path}")
        if file_path is None:
            file_path = get_local_cache_dir() / ("temp_file_" + uuid.uuid4().hex)

        bucket, key = self._parse_qumulo_path(gcs_path)

        async with self.session.client(**self._get_client_kwargs()) as s3_client:
            try:
                await s3_client.download_file(bucket, key, str(file_path))
                full_path = f"qumulo://{bucket}/{key}"
                logger.info(f"Successfully downloaded {full_path} to {file_path}")
                return full_path, str(file_path)
            except ClientError as e:
                logger.error(f"Failed to download {bucket}/{key}: {e}")
                raise

    @override
    async def upload_file(self, file_path: Path, gcs_path: str) -> str:
        """Upload a file from local filesystem to Qumulo S3."""
        logger.info(f"Uploading file: {file_path} to Qumulo: {gcs_path}")
        bucket, key = self._parse_qumulo_path(gcs_path)

        async with self.session.client(**self._get_client_kwargs()) as s3_client:
            try:
                await s3_client.upload_file(str(file_path), bucket, key)
                full_path = f"qumulo://{bucket}/{key}"
                logger.info(f"Successfully uploaded {file_path} to {full_path}")
                return full_path
            except ClientError as e:
                logger.error(f"Failed to upload {file_path} to {bucket}/{key}: {e}")
                raise

    @override
    async def upload_bytes(self, file_contents: bytes, gcs_path: str) -> str:
        """Upload bytes directly to Qumulo S3."""
        logger.info(f"Uploading {len(file_contents)} bytes to Qumulo: {gcs_path}")
        bucket, key = self._parse_qumulo_path(gcs_path)

        async with self.session.client(**self._get_client_kwargs()) as s3_client:
            try:
                await s3_client.put_object(Bucket=bucket, Key=key, Body=file_contents)
                full_path = f"qumulo://{bucket}/{key}"
                logger.info(f"Successfully uploaded {len(file_contents)} bytes to {full_path}")
                return full_path
            except ClientError as e:
                logger.error(f"Failed to upload bytes to {bucket}/{key}: {e}")
                raise

    @override
    async def get_modified_date(self, gcs_path: str) -> datetime:
        """Get the last modified timestamp of a Qumulo object."""
        logger.info(f"Getting modified date of Qumulo object: {gcs_path}")
        bucket, key = self._parse_qumulo_path(gcs_path)

        async with self.session.client(**self._get_client_kwargs()) as s3_client:
            try:
                response = await s3_client.head_object(Bucket=bucket, Key=key)
                last_modified: datetime = response["LastModified"]
                logger.info(f"Last modified date of {bucket}/{key}: {last_modified}")
                return last_modified
            except ClientError as e:
                logger.error(f"Failed to get modified date for {bucket}/{key}: {e}")
                raise

    @override
    async def get_listing(self, gcs_path: str) -> list[ListingItem]:
        """
        List objects in a Qumulo path prefix.

        Returns a list of ListingItem objects for all objects with the given prefix.
        This corresponds to listing a directory in the Qumulo filesystem.
        """
        logger.info(f"Getting listing of Qumulo path: {gcs_path}")
        bucket, prefix = self._parse_qumulo_path(gcs_path)

        # Ensure prefix ends with / for directory-style listing
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"

        async with self.session.client(**self._get_client_kwargs()) as s3_client:
            try:
                listing: list[ListingItem] = []
                paginator = s3_client.get_paginator("list_objects_v2")

                async for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    if "Contents" not in page:
                        continue

                    for obj in page["Contents"]:
                        listing.append(
                            ListingItem(
                                Key=obj["Key"],
                                LastModified=obj["LastModified"],
                                ETag=obj["ETag"],
                                Size=obj["Size"],
                            )
                        )

                logger.info(f"Found {len(listing)} objects in {bucket}/{prefix}")
                return listing
            except ClientError as e:
                logger.error(f"Failed to list objects in {bucket}/{prefix}: {e}")
                raise

    @override
    async def get_file_contents(self, gcs_path: str) -> bytes | None:
        """Download and return the contents of a Qumulo object as bytes."""
        logger.info(f"Getting contents of Qumulo object: {gcs_path}")
        bucket, key = self._parse_qumulo_path(gcs_path)

        async with self.session.client(**self._get_client_kwargs()) as s3_client:
            try:
                response = await s3_client.get_object(Bucket=bucket, Key=key)
                async with response["Body"] as stream:
                    contents: bytes = await stream.read()
                logger.info(f"Successfully read {len(contents)} bytes from {bucket}/{key}")
                return contents
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(f"Object not found: {bucket}/{key}")
                    return None
                logger.error(f"Failed to get contents of {bucket}/{key}: {e}")
                raise

    @override
    async def close(self) -> None:
        """Close the Qumulo S3 session. aioboto3 sessions are closed automatically via context managers."""
        logger.info("Closing Qumulo S3 session")
        # aioboto3.Session doesn't require explicit cleanup
        # Clients are closed via async context managers
        pass
