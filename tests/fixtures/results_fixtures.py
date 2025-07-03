import json
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio

from sms_api.common.hpc.sim_utils import read_latest_commit
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings


@pytest_asyncio.fixture(scope="function")
async def latest_commit():
    yield read_latest_commit()


@pytest_asyncio.fixture(scope="function")
async def expected_columns():
    with open("assets/tests/expected_columns.json") as fp:
        return json.load(fp)


@pytest_asyncio.fixture(scope="function")
async def ssh_service() -> AsyncGenerator[SSHService]:
    ssh_service = SSHService(
        hostname=get_settings().slurm_submit_host,
        username=get_settings().slurm_submit_user,
        key_path=Path(get_settings().slurm_submit_key_path),
    )
    yield ssh_service
    await ssh_service.close()
