import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import asyncssh
from asyncssh import SSHCompletedProcess

from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import Settings, get_settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SSHServiceManaged:
    hostname: str
    username: str
    key_path: Path
    known_hosts: str | None

    def __init__(self, hostname: str, username: str, key_path: Path, known_hosts: Path | None = None) -> None:
        self.hostname = hostname
        self.username = username
        self.key_path = key_path
        self.known_hosts = str(known_hosts) if known_hosts else None
        self.conn: asyncssh.SSHClientConnection | None = None

    @property
    def connected(self) -> bool:
        return self.conn is not None

    async def verify_connection(self, retry: bool = True, t_wait: float | None = None, _max_iter: int = 3) -> bool:
        """
        Verify that this instance is connected with ssh, and optionally attempt a retry loop if not.
        This should be run PRIOR to executing any ``SSHServiceManaged``-dependent logic.

        :param retry: If ``True``, attempt connection retry of a total of ``_max_iter`` attempts.
        :param t_wait: Amount of wait time to execute in running retry loop. Defaults to ``0.3``.
        :param _max_iter: Max number of retry attempts to execute when a connection cannot be established
            with ssh, if ``retry`` is ``True``. Defaults to ``3``.

        :return: (``bool``) Whether the analysis_service's ssh instance is connected (it should be!)
        """
        if not self.connected and retry:
            logger.info(
                f""" \
                SSH Service not connected. Attempting a reconnect {f"in {t_wait}s" if t_wait is not None else "now"}...
                """.upper()
            )
            i = 0
            while not self.connected:
                if i == _max_iter:
                    raise RuntimeError(f"Couldnt connect ssh service after {i} attempts!")
                if t_wait is not None:
                    await asyncio.sleep(t_wait)
                else:
                    await asyncio.sleep(0.3)

                await self.connect()
                if self.connected:
                    break
                else:
                    i += 1

        return self.connected

    async def connect(self) -> None:
        if self.conn is not None:  # and self.conn._connection_made():
            logger.debug("SSH Connection has already been made.")
            return
        try:
            self.conn = await asyncssh.connect(
                host=self.hostname,
                username=self.username,
                client_keys=[self.key_path],
                known_hosts=self.known_hosts,
                keepalive_interval=300,
            )
            logger.info(f">> Managed SSH Service Connected to {self.hostname} as {self.username}")
        except (OSError, asyncssh.Error) as exc:
            logger.exception(f"Failed to make a connection to {self.hostname}")
            raise RuntimeError(f"SSH connection failed: {str(exc)[:100]}") from exc

    async def disconnect(self) -> None:
        if self.conn:
            self.conn.close()
            try:
                await self.conn.wait_closed()
            except Exception as exc:
                logger.warning(f"Error while closing SSH connection: {exc}")
            finally:
                logger.info(f">> Managed SSH Service Closed SSH connection to {self.hostname}")
                self.conn = None

    async def run_command(self, command: str) -> tuple[int, str, str]:
        if self.conn is None:
            raise RuntimeError("SSH connection not established. Call connect() first.")
        try:
            logger.info(f"Running SSH command: {command}")
            result = await self.conn.run(command, check=True)

            if not isinstance(result.stdout, str):
                raise TypeError(f"Expected result.stdout to be str, got {type(result.stdout)}")
            if not isinstance(result.stderr, str):
                raise TypeError(f"Expected result.stderr to be str, got {type(result.stderr)}")
            if not isinstance(result.returncode, int):
                raise TypeError(f"Expected result.returncode to be int, got {type(result.returncode)}")
            logger.info(
                f"Command '{command}' retcode={result.returncode} "
                f"stdout={result.stdout[:100]} stderr={result.stderr[:100]!r}"
            )
            return result.returncode, result.stdout, result.stderr
        except asyncssh.ProcessError as exc:
            logger.exception(f"Command '{command}' failed: {exc.stderr[:100]!r}")
            raise RuntimeError(f"SSH command failed: {exc.stderr[:100]!r}") from exc
        except (OSError, asyncssh.Error) as exc:
            logger.exception(f"SSH error while running '{command}'")
            raise RuntimeError(f"SSH command error: {str(exc)[:100]}") from exc

    async def scp_upload(self, local_file: Path, remote_path: HPCFilePath, **kwargs: Any) -> None:
        if self.conn is None:
            raise RuntimeError("SSH connection not established. Call connect() first.")
        try:
            await asyncssh.scp(local_file, (self.conn, remote_path.remote_path), **kwargs)
            logger.info(f"Uploaded {local_file} -> {remote_path}")
        except asyncssh.Error as exc:
            logger.exception(f"Failed to upload {local_file}")
            raise RuntimeError(f"SCP upload failed: {str(exc)[:100]}") from exc

    async def scp_download(self, local_file: Path, remote_path: HPCFilePath) -> None:
        if self.conn is None:
            raise RuntimeError("SSH connection not established. Call connect() first.")
        try:
            await asyncssh.scp((self.conn, remote_path.remote_path), local_file)
            logger.info(f"Downloaded {remote_path} -> {local_file}")
        except asyncssh.Error as exc:
            logger.exception(f"Failed to download {remote_path}")
            raise RuntimeError(f"SCP download failed: {str(exc)[:100]}") from exc


class SSHService:
    hostname: str
    username: str
    key_path: Path
    known_hosts: str | None

    def __init__(self, hostname: str, username: str, key_path: Path, known_hosts: Path | None = None) -> None:
        self.hostname = hostname
        self.username = username
        self.key_path = key_path
        self.known_hosts = str(known_hosts) if known_hosts else None

    async def run_command(self, command: str) -> tuple[int, str, str]:
        async with asyncssh.connect(
            host=self.hostname,
            username=self.username,
            client_keys=[self.key_path],
            known_hosts=self.known_hosts,
            keepalive_interval=30,
        ) as conn:
            try:
                logger.info(f"Running ssh command: {command}")
                result: SSHCompletedProcess = await conn.run(command, check=True)
                if not isinstance(result.stdout, str):
                    raise TypeError(f"Expected result.stdout to be str, got {type(result.stdout)}")
                if not isinstance(result.stderr, str):
                    raise TypeError(f"Expected result.stderr to be str, got {type(result.stderr)}")
                if not isinstance(result.returncode, int):
                    raise TypeError(f"Expected result.returncode to be int, got {type(result.returncode)}")
                logger.info(
                    msg=f"command {command} retcode {result.returncode} "
                    f"stdout={result.stdout[:100]} stderr={result.stderr[:100]}"
                )
                return result.returncode, result.stdout, result.stderr
            except asyncssh.ProcessError as exc:
                logger.exception(msg=f"failed to send command {command}, stderr {str(exc.stderr)[:100]}", exc_info=exc)
                raise RuntimeError(f"failed to send command {command}, stderr {str(exc.stderr)[:100]})") from exc
            except (OSError, asyncssh.Error) as exc:
                logger.exception(msg=f"failed to send command {command}, stderr {str(exc)[:100]}", exc_info=exc)
                raise RuntimeError(f"failed to send command {command}, error {str(exc)[:100]}") from exc

    async def scp_upload(self, local_file: Path, remote_path: HPCFilePath, **kwargs) -> None:  # type: ignore[no-untyped-def]
        async with asyncssh.connect(
            host=self.hostname, username=self.username, client_keys=[self.key_path], known_hosts=self.known_hosts
        ) as conn:
            try:
                await asyncssh.scp(srcpaths=local_file, dstpath=(conn, remote_path.remote_path), **kwargs)
                logger.info(msg=f"sent file {local_file} to {remote_path}")
            except asyncssh.Error as exc:
                logger.exception(msg=f"failed to send file {local_file} to {remote_path}", exc_info=exc)
                raise RuntimeError(
                    f"failed to send file {local_file} to {remote_path}, error {str(exc)[:100]}"
                ) from exc

    async def scp_download(self, local_file: Path, remote_path: HPCFilePath) -> None:
        async with asyncssh.connect(
            host=self.hostname, username=self.username, client_keys=[self.key_path], known_hosts=self.known_hosts
        ) as conn:
            try:
                await asyncssh.scp(srcpaths=(conn, remote_path.remote_path), dstpath=local_file)
                logger.info(msg=f"retrieved remote file {remote_path} to {local_file}")
            except asyncssh.Error as exc:
                logger.exception(msg=f"failed to retrieve remote file {remote_path} to {local_file}", exc_info=exc)
                raise RuntimeError(
                    f"failed to retrieve remote file {remote_path} to {local_file}, error {str(exc)[:100]}"
                ) from exc

    async def close(self) -> None:
        pass  # nothing to do here because we don't yet keep the connection around.


class SSHSession:
    """A wrapper around an established SSH connection that provides command execution and file transfer."""

    def __init__(self, conn: asyncssh.SSHClientConnection, hostname: str) -> None:
        self._conn = conn
        self._hostname = hostname

    @property
    def connection(self) -> asyncssh.SSHClientConnection:
        """Access the underlying asyncssh connection."""
        return self._conn

    async def run_command(self, command: str) -> tuple[int, str, str]:
        """Run a command on the remote host.

        :param command: The command to execute
        :return: Tuple of (return_code, stdout, stderr)
        :raises RuntimeError: If the command fails
        """
        try:
            logger.info(f"Running SSH command: {command}")
            result: SSHCompletedProcess = await self._conn.run(command, check=True)

            if not isinstance(result.stdout, str):
                raise TypeError(f"Expected result.stdout to be str, got {type(result.stdout)}")
            if not isinstance(result.stderr, str):
                raise TypeError(f"Expected result.stderr to be str, got {type(result.stderr)}")
            if not isinstance(result.returncode, int):
                raise TypeError(f"Expected result.returncode to be int, got {type(result.returncode)}")

            logger.info(
                f"Command '{command}' retcode={result.returncode} "
                f"stdout={result.stdout[:100]} stderr={result.stderr[:100]!r}"
            )
            return result.returncode, result.stdout, result.stderr
        except asyncssh.ProcessError as exc:
            logger.exception(f"Command '{command}' failed: {exc.stderr[:100]!r}")
            raise RuntimeError(f"SSH command failed: {exc.stderr[:100]!r}") from exc
        except (OSError, asyncssh.Error) as exc:
            logger.exception(f"SSH error while running '{command}'")
            raise RuntimeError(f"SSH command error: {str(exc)[:100]}") from exc

    async def scp_upload(self, local_file: Path, remote_path: HPCFilePath, **kwargs: Any) -> None:
        """Upload a file to the remote host via SCP.

        :param local_file: Path to the local file
        :param remote_path: Remote destination path
        :raises RuntimeError: If the upload fails
        """
        try:
            await asyncssh.scp(local_file, (self._conn, remote_path.remote_path), **kwargs)
            logger.info(f"Uploaded {local_file} -> {remote_path}")
        except asyncssh.Error as exc:
            logger.exception(f"Failed to upload {local_file}")
            raise RuntimeError(f"SCP upload failed: {str(exc)[:100]}") from exc

    async def scp_download(self, local_file: Path, remote_path: HPCFilePath) -> None:
        """Download a file from the remote host via SCP.

        :param local_file: Local destination path
        :param remote_path: Path to the remote file
        :raises RuntimeError: If the download fails
        """
        try:
            await asyncssh.scp((self._conn, remote_path.remote_path), local_file)
            logger.info(f"Downloaded {remote_path} -> {local_file}")
        except asyncssh.Error as exc:
            logger.exception(f"Failed to download {remote_path}")
            raise RuntimeError(f"SCP download failed: {str(exc)[:100]}") from exc


class SSHSessionService:
    """SSH service that provides sessions via an async context manager.

    Each session creates a fresh SSH connection, verifies it with a ping,
    and cleanly closes it when the context exits.

    Example:
        service = SSHSessionService(hostname="example.com", username="user", key_path=Path("~/.ssh/id_rsa"))
        async with service.session() as ssh:
            retcode, stdout, stderr = await ssh.run_command("ls -la")
    """

    def __init__(
        self,
        hostname: str,
        username: str,
        key_path: Path,
        known_hosts: Path | None = None,
        keepalive_interval: int = 30,
    ) -> None:
        self.hostname = hostname
        self.username = username
        self.key_path = key_path
        self.known_hosts = str(known_hosts) if known_hosts else None
        self.keepalive_interval = keepalive_interval

    @asynccontextmanager
    async def session(self, wait_closed: bool = True) -> AsyncIterator[SSHSession]:
        """Create and yield an SSH session.

        Creates a new SSH connection, verifies it with a ping command,
        then yields an SSHSession for command execution. On exit, the
        connection is closed.

        :param wait_closed: If True (default), wait for the connection to fully close
            before returning from the context manager. Set to False for faster exit
            when you don't need to guarantee the connection is fully terminated.
        :yields: An SSHSession instance for running commands and transferring files
        :raises RuntimeError: If connection or verification fails
        """
        conn: asyncssh.SSHClientConnection | None = None
        try:
            logger.info(f"Opening SSH session to {self.hostname} as {self.username}")
            conn = await asyncssh.connect(
                host=self.hostname,
                username=self.username,
                client_keys=[self.key_path],
                known_hosts=self.known_hosts,
                keepalive_interval=self.keepalive_interval,
            )

            # Verify connection with a ping
            result = await conn.run("echo ping", check=True)
            if result.stdout is None or "ping" not in result.stdout:
                raise RuntimeError("SSH connection verification failed: ping did not return expected output")

            logger.info(f"SSH session established and verified to {self.hostname}")
            yield SSHSession(conn, self.hostname)

        except (OSError, asyncssh.Error) as exc:
            logger.exception(f"Failed to establish SSH session to {self.hostname}")
            raise RuntimeError(f"SSH session failed: {str(exc)[:100]}") from exc

        finally:
            if conn is not None:
                logger.info(f"Closing SSH session to {self.hostname}")
                conn.close()
                if wait_closed:
                    try:
                        await conn.wait_closed()
                        logger.info(f"SSH session to {self.hostname} fully closed")
                    except Exception as exc:
                        logger.warning(f"Error while waiting for SSH connection to close: {exc}")
                else:
                    logger.info(f"SSH session to {self.hostname} close initiated (not waiting)")


def get_ssh_service() -> SSHService:
    ssh_settings = get_settings()
    return SSHService(
        hostname=ssh_settings.slurm_submit_host,
        username=ssh_settings.slurm_submit_user,
        key_path=Path(ssh_settings.slurm_submit_key_path),
        known_hosts=Path(ssh_settings.slurm_submit_known_hosts) if ssh_settings.slurm_submit_known_hosts else None,
    )


def get_ssh_service_managed(env: Settings | None = None) -> SSHServiceManaged:
    ssh_settings = env or get_settings()
    return SSHServiceManaged(
        hostname=ssh_settings.slurm_submit_host,
        username=ssh_settings.slurm_submit_user,
        key_path=Path(ssh_settings.slurm_submit_key_path),
        known_hosts=Path(ssh_settings.slurm_submit_known_hosts) if ssh_settings.slurm_submit_known_hosts else None,
    )


def create_ssh_session_service(env: Settings | None = None) -> SSHSessionService:
    """Create a new SSHSessionService instance using settings from environment.

    Note: For singleton access, use get_ssh_session_service() from sms_api.dependencies instead.

    :param env: Optional Settings object. If not provided, uses get_settings()
    :return: New SSHSessionService instance
    """
    ssh_settings = env or get_settings()
    return SSHSessionService(
        hostname=ssh_settings.slurm_submit_host,
        username=ssh_settings.slurm_submit_user,
        key_path=Path(ssh_settings.slurm_submit_key_path),
        known_hosts=Path(ssh_settings.slurm_submit_known_hosts) if ssh_settings.slurm_submit_known_hosts else None,
    )
