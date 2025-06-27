import asyncio
import os
import sys

import asyncssh
import pytest
import pytest_asyncio

HPC_HOST = "login.hpc.cam.uchc.edu"
HPC_USER = "svc_vivarium"


def get_key_path() -> str:
    args = sys.argv
    for arg in args:
        if arg.startswith("key="):
            return arg.split("=")[-1]
    return os.path.join(os.getenv("HOME", "/Users/alexanderpatrie"), ".ssh", "sms_id_rsa")


async def run_test_ssh(host: str, username: str, key_fp: str) -> bool:
    try:
        async with asyncssh.connect(
            host=host,
            username=username,
            client_keys=[key_fp],
            known_hosts=None,  # optional: disables host key checking
        ) as conn:
            result = await conn.run("echo ping && whoami && echo $HOME", check=True)
            stdout = result.stdout.decode() if isinstance(result.stdout, bytes) else result.stdout
            if stdout is not None:
                print(f"Connection successful.\nOutput: {stdout.strip()}")
                return True
            else:
                return False
    except (asyncssh.Error, OSError) as e:
        print(f"SSH connection failed: {e}")
        return False


@pytest_asyncio.fixture(scope="session")
async def hpc_host() -> str:
    return HPC_HOST


@pytest_asyncio.fixture(scope="session")
async def hpc_user() -> str:
    return HPC_USER


@pytest_asyncio.fixture(scope="session")
async def key_path() -> str:
    return get_key_path()


@pytest.mark.asyncio
async def test_asyncssh(hpc_host: str, hpc_user: str, key_path: str) -> bool:
    return await run_test_ssh(hpc_host, hpc_user, key_path)


if __name__ == "__main__":
    asyncio.run(run_test_ssh(host="login.hpc.cam.uchc.edu", username="svc_vivarium", key_fp=get_key_path()))
