import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged, SSHSession, SSHSessionService
from sms_api.common.storage.file_paths import HPCFilePath
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

    remote_path = HPCFilePath(remote_path=Path(f"remote_temp_{uuid.uuid4().hex}.txt"))
    local_path_2 = Path("temp2.txt")

    await ssh_service.scp_upload(local_file=local_path, remote_path=remote_path)
    await ssh_service.scp_download(remote_path=remote_path, local_file=local_path_2)

    with open(local_path_2) as f:
        assert f.read() == "hello world"

    return_code, stdout, stderr = await ssh_service.run_command(f"rm {remote_path}")
    assert return_code == 0
    local_path.unlink()
    local_path_2.unlink()


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_ssh_service_managed() -> None:
    ssh_settings = get_settings()
    ssh = SSHServiceManaged(
        hostname=ssh_settings.slurm_submit_host,
        username=ssh_settings.slurm_submit_user,
        key_path=Path(ssh_settings.slurm_submit_key_path),
        known_hosts=Path(ssh_settings.slurm_submit_known_hosts) if ssh_settings.slurm_submit_known_hosts else None,
    )
    await ssh.connect()
    try:
        retcode, stdout, stderr = await ssh.run_command("echo $USER")
        assert ssh_settings.slurm_submit_user in stdout
    finally:
        await ssh.disconnect()


# ----------------------- SSHSessionService Tests -----------------------


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_ssh_session_service_run_command() -> None:
    """Integration test: SSHSessionService can run commands via session context manager."""
    ssh_settings = get_settings()
    service = SSHSessionService(
        hostname=ssh_settings.slurm_submit_host,
        username=ssh_settings.slurm_submit_user,
        key_path=Path(ssh_settings.slurm_submit_key_path),
        known_hosts=Path(ssh_settings.slurm_submit_known_hosts) if ssh_settings.slurm_submit_known_hosts else None,
    )

    async with service.session() as ssh:
        retcode, stdout, stderr = await ssh.run_command("echo $USER")
        assert retcode == 0
        assert ssh_settings.slurm_submit_user in stdout


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_ssh_session_service_scp_upload_download() -> None:
    """Integration test: SSHSessionService can upload and download files."""
    ssh_settings = get_settings()
    service = SSHSessionService(
        hostname=ssh_settings.slurm_submit_host,
        username=ssh_settings.slurm_submit_user,
        key_path=Path(ssh_settings.slurm_submit_key_path),
        known_hosts=Path(ssh_settings.slurm_submit_known_hosts) if ssh_settings.slurm_submit_known_hosts else None,
    )

    local_path = Path("temp_session_test.txt")
    with open(local_path, "w") as f:
        f.write("session test content")

    remote_path = HPCFilePath(remote_path=Path(f"remote_session_temp_{uuid.uuid4().hex}.txt"))
    local_path_2 = Path("temp_session_test2.txt")

    try:
        async with service.session() as ssh:
            await ssh.scp_upload(local_file=local_path, remote_path=remote_path)
            await ssh.scp_download(remote_path=remote_path, local_file=local_path_2)
            await ssh.run_command(f"rm {remote_path}")

        with open(local_path_2) as f:
            assert f.read() == "session test content"
    finally:
        local_path.unlink(missing_ok=True)
        local_path_2.unlink(missing_ok=True)


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_ssh_session_service_wait_closed_false() -> None:
    """Integration test: SSHSessionService works with wait_closed=False."""
    ssh_settings = get_settings()
    service = SSHSessionService(
        hostname=ssh_settings.slurm_submit_host,
        username=ssh_settings.slurm_submit_user,
        key_path=Path(ssh_settings.slurm_submit_key_path),
        known_hosts=Path(ssh_settings.slurm_submit_known_hosts) if ssh_settings.slurm_submit_known_hosts else None,
    )

    async with service.session(wait_closed=False) as ssh:
        retcode, stdout, stderr = await ssh.run_command("hostname")
        assert retcode == 0


@pytest.mark.asyncio
async def test_ssh_session_service_context_manager_closes_connection() -> None:
    """Unit test: verify context manager properly closes connection on exit."""
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="ping", returncode=0))
    mock_conn.close = MagicMock()
    mock_conn.wait_closed = AsyncMock()

    with patch("sms_api.common.ssh.ssh_service.asyncssh.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn

        service = SSHSessionService(
            hostname="test-host",
            username="test-user",
            key_path=Path("/fake/key"),
        )

        async with service.session() as ssh:
            assert isinstance(ssh, SSHSession)
            assert ssh.connection == mock_conn

        # Verify connection was closed and waited
        mock_conn.close.assert_called_once()
        mock_conn.wait_closed.assert_called_once()


@pytest.mark.asyncio
async def test_ssh_session_service_ping_verification() -> None:
    """Unit test: verify ping is executed to validate connection."""
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="ping", returncode=0))
    mock_conn.close = MagicMock()
    mock_conn.wait_closed = AsyncMock()

    with patch("sms_api.common.ssh.ssh_service.asyncssh.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn

        service = SSHSessionService(
            hostname="test-host",
            username="test-user",
            key_path=Path("/fake/key"),
        )

        async with service.session():
            pass

        # Verify ping was executed during connection setup
        mock_conn.run.assert_called_once_with("echo ping", check=True)


@pytest.mark.asyncio
async def test_ssh_session_service_ping_failure_raises() -> None:
    """Unit test: verify failure when ping doesn't return expected output."""
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="unexpected", returncode=0))
    mock_conn.close = MagicMock()
    mock_conn.wait_closed = AsyncMock()

    with patch("sms_api.common.ssh.ssh_service.asyncssh.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn

        service = SSHSessionService(
            hostname="test-host",
            username="test-user",
            key_path=Path("/fake/key"),
        )

        with pytest.raises(RuntimeError, match="ping did not return expected output"):
            async with service.session():
                pass

        # Connection should still be closed even on failure
        mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_ssh_session_service_no_wait_closed() -> None:
    """Unit test: verify wait_closed=False skips waiting for connection close."""
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="ping", returncode=0))
    mock_conn.close = MagicMock()
    mock_conn.wait_closed = AsyncMock()

    with patch("sms_api.common.ssh.ssh_service.asyncssh.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_conn

        service = SSHSessionService(
            hostname="test-host",
            username="test-user",
            key_path=Path("/fake/key"),
        )

        async with service.session(wait_closed=False):
            pass

        # Connection closed but wait_closed not called
        mock_conn.close.assert_called_once()
        mock_conn.wait_closed.assert_not_called()


@pytest.mark.asyncio
async def test_ssh_session_run_command() -> None:
    """Unit test: SSHSession.run_command delegates to connection."""
    mock_conn = MagicMock()
    mock_conn.run = AsyncMock(return_value=MagicMock(stdout="output", stderr="", returncode=0))

    session = SSHSession(mock_conn, "test-host")
    retcode, stdout, stderr = await session.run_command("test command")

    assert retcode == 0
    assert stdout == "output"
    assert stderr == ""
    mock_conn.run.assert_called_once_with("test command", check=True)
