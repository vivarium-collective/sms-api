import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import asyncssh
from asyncssh import SSHCompletedProcess

from sms_api.common.storage.file_paths import HPCFilePath

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
