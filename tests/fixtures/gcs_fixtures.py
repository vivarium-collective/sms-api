from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from gcloud.aio.auth import Token

from sms_api.common.storage import FileServiceGCS, create_token
from sms_api.config import get_local_cache_dir
from sms_api.dependencies import get_file_service, set_file_service
from tests.fixtures.file_service_local import FileServiceLocal

temp_data_dir = get_local_cache_dir() / "test_temp_dir"
temp_data_dir.mkdir(exist_ok=True)

@pytest_asyncio.fixture(scope="function")
async def temp_test_data_dir() -> AsyncGenerator[Path, None]:
    temp_data_dir.mkdir(exist_ok=True)

    yield temp_data_dir

    for file in temp_data_dir.iterdir():
        file.unlink()
    temp_data_dir.rmdir()


@pytest_asyncio.fixture(scope="function")
async def file_service_local() -> AsyncGenerator[FileServiceLocal, None]:
    file_service_local = FileServiceLocal()
    file_service_local.init()
    saved_file_service = get_file_service()
    set_file_service(file_service_local)

    yield file_service_local

    await file_service_local.close()
    set_file_service(saved_file_service)


@pytest_asyncio.fixture(scope="function")
async def file_service_gcs() -> AsyncGenerator[FileServiceGCS, None]:
    file_service_gcs: FileServiceGCS = FileServiceGCS()
    saved_file_service = get_file_service()
    set_file_service(file_service_gcs)

    yield file_service_gcs

    await file_service_gcs.close()
    set_file_service(saved_file_service)


@pytest_asyncio.fixture(scope="function")
async def file_service_gcs_test_base_path() -> Path:
    return Path("verify_test")


@pytest_asyncio.fixture(scope="module")
async def gcs_token() -> AsyncGenerator[Token, None]:
    token: Token = create_token()

    yield token

    await token.close()
