import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Generator

import pytest


@pytest.fixture(scope="module")
def socket_path() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "slurm_broker.sock")


@pytest.fixture(scope="module")
def broker_and_fake_sbatch(socket_path: str) -> Generator[str, None, None]:
    # Create a fake sbatch script for testing
    with tempfile.TemporaryDirectory() as tempdir:
        fake_sbatch = os.path.join(tempdir, "sbatch")
        with open(fake_sbatch, "w") as f:
            f.write("#!/bin/sh\necho FAKE_SBATCH_OK\n")
        os.chmod(fake_sbatch, 0o500)

        # Patch ALLOWED_COMMANDS in the broker to use our fake sbatch
        broker_path = os.path.abspath("../fixtures/scripts/slurm_broker.py")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        env["FAKE_SBATCH"] = fake_sbatch

        # Start the broker as a subprocess
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, broker_path, socket_path],
            env=env,
        )
        # Wait for the socket to appear
        for _ in range(20):
            if os.path.exists(socket_path):
                break
            time.sleep(0.1)
        else:
            proc.terminate()
            raise RuntimeError("Broker socket did not appear")

        yield fake_sbatch

        proc.terminate()
        proc.wait(timeout=5)


def test_sbatch(broker_and_fake_sbatch: str, socket_path: str) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(b"sbatch --help\n")
        data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            data += chunk
    assert b"FAKE_SBATCH_OK" in data


def test_invalid_command(broker_and_fake_sbatch: str, socket_path: str) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(socket_path)
        client.sendall(b"notallowed\n")
        data = client.recv(4096)
    assert b"ERROR: Command not allowed" in data
