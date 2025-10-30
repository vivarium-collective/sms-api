import os
import uuid
from pathlib import Path

import pytest

from sms_api.common.storage.file_service_gcs import FileServiceGCS
from sms_api.config import get_settings
from tests.fixtures.file_service_local import FileServiceLocal


@pytest.mark.asyncio
async def test_file_service_local(file_service_local: FileServiceLocal) -> None:
    expected_file_content = b"Hello, World!"
    file_service = file_service_local
    gcs_path = "some/gcs/path/fname.txt"
    orig_file_path = Path("temp.txt")

    with open(orig_file_path, "wb") as f:
        f.write(expected_file_content)

    # upload the file
    returned_gcs_path = await file_service.upload_file(orig_file_path, gcs_path)
    assert returned_gcs_path == gcs_path

    # download the file
    new_file_path = Path("temp2.txt")
    await file_service.download_file(gcs_path, new_file_path)
    assert new_file_path.exists()
    with open(new_file_path, "rb") as f:
        content = f.read()
        assert content == expected_file_content

    os.remove(orig_file_path)
    os.remove(new_file_path)


@pytest.mark.skipif(
    len(get_settings().storage_gcs_credentials_file) == 0, reason="gcs_credentials.json file not supplied"
)
@pytest.mark.asyncio
async def test_file_service_gcs(file_service_gcs: FileServiceGCS, file_service_gcs_test_base_path: Path) -> None:
    expected_file_content = b"Hello, World!"
    file_service = file_service_gcs

    gcs_path = str(file_service_gcs_test_base_path / "test_file_service_gcs" / f"fname-{uuid.uuid4().hex}.txt")
    orig_file_path = Path("temp.txt")

    with open(orig_file_path, "wb") as f:
        f.write(expected_file_content)

    # upload the file
    absolute_gcs_path = await file_service.upload_file(file_path=orig_file_path, gcs_path=gcs_path)
    assert absolute_gcs_path is not None

    # download the file
    new_file_path = Path("temp2.txt")
    await file_service.download_file(gcs_path=gcs_path, file_path=new_file_path)
    assert new_file_path.exists()
    with open(new_file_path, "rb") as f:
        content = f.read()
        assert content == expected_file_content

    os.remove(orig_file_path)
    os.remove(new_file_path)
