import asyncio
import os
import sys
from pathlib import Path

import asyncssh

TEST_KEY_PATH = os.path.join(os.getenv("HOME", "/Users/alexanderpatrie"), ".ssh", "sms_id_rsa")
HPC_HOST = "login.hpc.cam.uchc.edu"
HPC_USER = "svc_vivarium"


def get_key_path() -> Path:
    args = sys.argv
    return Path(args[1]) if len(args) > 1 else Path(os.getenv("HOME", "/Users/alexanderpatrie")) / ".ssh" / "sms_id_rsa"


async def test_ssh(host: str, username: str, key_fp: Path) -> bool:
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


if __name__ == "__main__":
    asyncio.run(test_ssh(host="login.hpc.cam.uchc.edu", username="svc_vivarium", key_fp=get_key_path()))
