import os
from datetime import datetime
from pathlib import Path

import pytest
from gcloud.aio.auth import Token

from sms_api.common.storage import ListingItem, download_gcs_file, get_gcs_modified_date, get_listing_of_gcs_path
from sms_api.config import get_settings

ROOT_DIR = Path(__file__).parent.parent.parent


@pytest.mark.skipif(
    len(get_settings().storage_gcs_credentials_file) == 0, reason="gcs_credentials.json file not supplied"
)
@pytest.mark.asyncio
async def test_download_gcs_file(temp_test_data_dir: Path, gcs_token: Token) -> None:
    RUN_ID = "61fd573874bc0ce059643515"
    GCS_PATH = f"simulations/{RUN_ID}/contents/reports.h5"
    LOCAL_PATH = temp_test_data_dir / f"{RUN_ID}.h5"

    await download_gcs_file(gcs_path=GCS_PATH, file_path=LOCAL_PATH, token=gcs_token)

    assert LOCAL_PATH.exists()

    os.remove(LOCAL_PATH)


@pytest.mark.skipif(
    len(get_settings().storage_gcs_credentials_file) == 0, reason="gcs_credentials.json file not supplied"
)
@pytest.mark.asyncio
async def test_get_gcs_modified_date(gcs_token: Token) -> None:
    RUN_ID = "61fd573874bc0ce059643515"
    GCS_PATH = f"simulations/{RUN_ID}/contents/reports.h5"

    td = await get_gcs_modified_date(gcs_path=GCS_PATH, token=gcs_token)
    assert type(td) is datetime


@pytest.mark.skipif(
    len(get_settings().storage_gcs_credentials_file) == 0, reason="gcs_credentials.json file not supplied"
)
@pytest.mark.asyncio
async def test_get_listing_of_gcs_path(gcs_token: Token) -> None:
    RUN_ID = "61fd573874bc0ce059643515"
    GCS_PATH = f"simulations/{RUN_ID}/contents"

    files = await get_listing_of_gcs_path(gcs_path=GCS_PATH, token=gcs_token)
    assert len(files) > 0
    assert type(files[0]) is ListingItem
