import uuid
from pathlib import Path

import pytest

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_ssh_command(ssh_service: SSHService) -> None:
    return_code, stdout, stderr = await ssh_service.run_command("hostname")
    assert return_code == 0
    # assert stdout.strip("\n") == ssh_service.hostname  # hostname may be different if behind a proxy server


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_scp_upload_download(ssh_service: SSHService) -> None:
    # create local temp text file with content "hello world"
    local_path = Path("temp.txt")
    with open(local_path, "w") as f:
        f.write("hello world")

    remote_path = Path(f"remote_temp_{uuid.uuid4().hex}.txt")
    local_path_2 = Path("temp2.txt")

    await ssh_service.scp_upload(local_file=local_path, remote_path=remote_path)
    await ssh_service.scp_download(remote_path=remote_path, local_file=local_path_2)

    with open(local_path_2) as f:
        assert f.read() == "hello world"

    return_code, stdout, stderr = await ssh_service.run_command(f"rm {remote_path}")
    assert return_code == 0
    local_path.unlink()
    local_path_2.unlink()
