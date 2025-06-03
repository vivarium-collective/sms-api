import logging
import uuid

from temporalio import workflow

from biosim_server.common.storage.gcs_aio import create_token, close_token, download_gcs_file, upload_file_to_gcs, \
    upload_bytes_to_gcs, get_gcs_modified_date, get_listing_of_gcs_path, get_gcs_file_contents
from biosim_server.config import get_local_cache_dir

with workflow.unsafe.imports_passed_through():
    from datetime import datetime
from pathlib import Path
from typing import Optional
from gcloud.aio.auth import Token

from typing_extensions import override

from biosim_server.common.storage.file_service import FileService, ListingItem


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class FileServiceGCS(FileService):
    token: Token

    def __init__(self) -> None:
        self.token = create_token()

    @override
    async def download_file(self, gcs_path: str, file_path: Optional[Path]=None) -> tuple[str, str]:
        logger.info(f"Downloading {gcs_path} to {file_path}")
        if file_path is None:
            file_path = get_local_cache_dir() / ("temp_file_"+uuid.uuid4().hex)
        full_gcs_path = await download_gcs_file(gcs_path=gcs_path, file_path=file_path, token=self.token)
        return full_gcs_path, str(file_path)

    @override
    async def upload_file(self, file_path: Path, gcs_path: str) -> str:
        logger.info(f"Uploading {file_path} to {gcs_path}")
        return await upload_file_to_gcs(file_path=file_path, gcs_path=gcs_path, token=self.token)

    @override
    async def upload_bytes(self, file_contents: bytes, gcs_path: str) -> str:
        logger.info(f"Uploading {len(file_contents)} bytes to {gcs_path}")
        return await upload_bytes_to_gcs(file_contents=file_contents, gcs_path=gcs_path, token=self.token)

    @override
    async def get_modified_date(self, gcs_path: str) -> datetime:
        logger.info(f"Getting modified date of {gcs_path}")
        return await get_gcs_modified_date(gcs_path=gcs_path, token=self.token)

    @override
    async def get_listing(self, gcs_path: str) -> list[ListingItem]:
        logger.info(f"Getting listing of {gcs_path}")
        return await get_listing_of_gcs_path(gcs_path, token=self.token)

    @override
    async def get_file_contents(self, gcs_path: str) -> bytes | None:
        logger.info(f"Getting contents of {gcs_path}")
        return await get_gcs_file_contents(gcs_path=gcs_path, token=self.token)

    @override
    async def close(self) -> None:
        await close_token(self.token)
