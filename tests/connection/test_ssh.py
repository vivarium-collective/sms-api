import asyncio
import os
import asyncssh
import pytest


default_home = '/Users/alexanderpatrie'
test_key_path = os.path.join(
    os.getenv('HOME', default_home),
    '.ssh',
    'sms_id_rsa'
)
hpc_host="login.hpc.cam.uchc.edu"
hpc_username="svc_vivarium"

# @pytest.mark.asyncio
async def test_asyncssh_connection(host: str, username: str, key_path: str):
    try:
        async with asyncssh.connect(
            host=host,
            username=username,
            client_keys=[key_path],
            known_hosts=None  # optional: disables host key checking
        ) as conn:
            result = await conn.run('echo ping && ls -al', check=True)
            print(f"Connection successful. Output: {result.stdout.strip()}")
            return True
    except (asyncssh.Error, OSError) as e:
        print(f"SSH connection failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(
        test_asyncssh_connection(
            host="login.hpc.cam.uchc.edu", 
            username="svc_vivarium", 
            key_path=test_key_path
        )
    )
