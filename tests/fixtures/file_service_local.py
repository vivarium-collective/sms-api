import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import aiofiles
from typing_extensions import override

from sms_api.common.storage.file_service import FileService, ListingItem
from sms_api.config import get_local_cache_dir

logger = logging.getLogger(__name__)


def generate_fake_etag(file_path: Path) -> str:
    return file_path.absolute().as_uri()


class FileServiceLocal(FileService):
    # temporary base directory for the mock GCS file store
    BASE_DIR_PARENT = get_local_cache_dir() / "local_data"
    BASE_DIR_PARENT.mkdir(exist_ok=True)
    BASE_DIR = BASE_DIR_PARENT / ("gcs_" + uuid.uuid4().hex)

    gcs_files_written: list[Path] = []

    def init(self) -> None:
        self.BASE_DIR.mkdir(parents=True, exist_ok=False)

    @override
    async def close(self) -> None:
        # remove all files in the mock gcs file store
        shutil.rmtree(self.BASE_DIR)

    @override
    async def download_file(self, gcs_path: str, file_path: Path | None = None) -> tuple[str, str]:
        logger.info(f"Downloading {gcs_path} to {file_path}")
        if file_path is None:
            file_path = get_local_cache_dir() / ("temp_file_" + uuid.uuid4().hex)
        # copy file from mock gcs to local file system
        gcs_file_path = self.BASE_DIR / gcs_path
        local_file_path = Path(file_path)
        local_file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(gcs_file_path, mode="rb") as f:
            contents = await f.read()
            async with aiofiles.open(local_file_path, mode="wb") as f2:
                await f2.write(contents)
        return str(gcs_path), str(local_file_path)

    @override
    async def upload_file(self, file_path: Path, gcs_path: str) -> str:
        logger.info(f"Uploading {file_path} to {gcs_path}")
        # copy file from local file_path to mock gcs using aoifiles
        local_file_path = Path(file_path)
        gcs_file_path = self.BASE_DIR / gcs_path
        gcs_file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(local_file_path, mode="rb") as f:
            contents = await f.read()
            async with aiofiles.open(gcs_file_path, mode="wb") as f2:
                await f2.write(contents)
        self.gcs_files_written.append(gcs_file_path)
        return str(gcs_path)

    @override
    async def upload_bytes(self, file_contents: bytes, gcs_path: str) -> str:
        logger.info(f"Uploading bytes to {gcs_path}")
        # write bytes to mock gcs
        gcs_file_path = self.BASE_DIR / gcs_path
        gcs_file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(gcs_file_path, mode="wb") as f:
            await f.write(file_contents)
        self.gcs_files_written.append(gcs_file_path)
        return str(gcs_path)

    @override
    async def get_modified_date(self, gcs_path: str) -> datetime:
        # get the modified date of the file in mock gcs
        gcs_file_path = self.BASE_DIR / gcs_path
        return datetime.fromtimestamp(gcs_file_path.stat().st_mtime)

    @override
    async def get_listing(self, gcs_path: str) -> list[ListingItem]:
        # get the listing of the directory in mock gcs
        gcs_dir_path = self.BASE_DIR / gcs_path
        return [
            ListingItem(
                Key=str(file.relative_to(self.BASE_DIR)),
                Size=file.stat().st_size,
                LastModified=datetime.fromtimestamp(file.stat().st_mtime),
                ETag=generate_fake_etag(file),
            )
            for file in gcs_dir_path.rglob("*")
        ]

    @override
    async def get_file_contents(self, gcs_path: str) -> bytes | None:
        # get the file contents from mock gcs
        gcs_file_path = self.BASE_DIR / gcs_path
        if not gcs_file_path.exists():
            return None
        return gcs_file_path.read_bytes()
