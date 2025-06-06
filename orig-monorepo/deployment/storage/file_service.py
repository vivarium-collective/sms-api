from abc import ABC, abstractmethod

from pydantic import BaseModel
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from datetime import datetime
from pathlib import Path
from typing import Optional


class ListingItem(BaseModel):
    Key: str
    LastModified: datetime
    ETag: str
    Size: int


class FileService(ABC):

    @abstractmethod
    async def download_file(self, gcs_path: str, file_path: Optional[Path] = None) -> tuple[str, str]:
        pass

    @abstractmethod
    async def upload_file(self, file_path: Path, gcs_path: str) -> str:
        pass

    @abstractmethod
    async def upload_bytes(self, file_contents: bytes, gcs_path: str) -> str:
        pass

    @abstractmethod
    async def get_modified_date(self, gcs_path: str) -> datetime:
        pass

    @abstractmethod
    async def get_listing(self, gcs_path: str) -> list[ListingItem]:
        pass

    @abstractmethod
    async def get_file_contents(self, gcs_path: str) -> bytes | None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass