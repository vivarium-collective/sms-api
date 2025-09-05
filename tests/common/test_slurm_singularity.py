import asyncio
import tempfile
import time
from pathlib import Path
from textwrap import dedent

import pytest

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmServiceRemoteHPC, SlurmServiceLocalHPC
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings

singularity_container_image = "slurm_test.sif"

slurm_broker_py_contents = dedent("""
import asyncio
import os
import socket
import struct
import sys
from asyncio import StreamReader, StreamWriter

ALLOWED_COMMANDS = {
    "/usr/bin/sbatch": ["sbatch"],
    "/usr/bin/squeue": ["squeue"],
    "/usr/bin/sacct": ["sacct"],
}

async def handle_client(reader: StreamReader, writer: StreamWriter) -> None:
    try:
        sock = writer.get_extra_info("socket")
        ucred = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
        pid, peer_uid, gid = struct.unpack("3i", ucred)
        if peer_uid != os.getuid():
            writer.write(b"ERROR: UID mismatch\\n")
            await writer.drain()
            writer.close()
            return

        data = await reader.readline()
        if not data:
            writer.close()
            return
        parts = data.decode().strip().split()
        if not parts or parts[0] not in ALLOWED_COMMANDS.keys():
            writer.write(f"ERROR: Command '{parts}' not allowed\\n".encode())
            await writer.drain()
            writer.close()
            return
        cmd = list(ALLOWED_COMMANDS[parts[0]]) + parts[1:]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        writer.write(stdout)
        if stderr:
            writer.write(b"\\nERROR:\\n" + stderr)
        await writer.drain()
    except Exception as e:
        writer.write(f"ERROR: {e}\\n".encode())
        await writer.drain()
    finally:
        writer.close()

async def main(socket_path: str) -> None:
    if os.path.exists(socket_path):
        os.remove(socket_path)
    server = await asyncio.start_unix_server(handle_client, path=socket_path)
    os.chmod(socket_path, 0o700)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print(f"Usage: {sys.argv[0]} SOCKET_PATH")
        sys.exit(1)
    socket_path = sys.argv[1]
    try:
        asyncio.run(main(socket_path))
    except KeyboardInterrupt:
        print("Broker stopped.")
""")


singularity_def_contents = dedent("""
    Bootstrap: docker
    From: alpine:latest

    %post
        apk add --no-cache socat bash

        cat <<'EOF' > /usr/bin/sbatch
    #!/bin/sh
    echo "$0 $@" | socat - UNIX-CONNECT:$UNIX_SOCKET_PATH
    EOF
        chmod +x /usr/bin/sbatch

        cat <<'EOF' > /usr/bin/squeue
    #!/bin/sh
    echo "$0 $@" | socat - UNIX-CONNECT:$UNIX_SOCKET_PATH
    EOF
        chmod +x /usr/bin/squeue

        cat <<'EOF' > /usr/bin/sacct
    #!/bin/sh
    echo "$0 $@" | socat - UNIX-CONNECT:$UNIX_SOCKET_PATH
    EOF
        chmod +x /usr/bin/sacct

    """)


sbatch_file_contents = dedent(f"""\
#!/bin/bash
#SBATCH --job-name=my_test_job        # Job name
#SBATCH --output=slurm_test.out       # Standard output file (same)
#SBATCH --error=slurm_test.out        # Standard error file (same)
#SBATCH --partition={get_settings().slurm_partition}       # Partition or queue name
#SBATCH --qos={get_settings().slurm_qos}                   # QOS level
#SBATCH --nodelist={get_settings().slurm_node_list}  # List of nodes
#SBATCH --nodes=1                     # Number of nodes
#SBATCH --ntasks-per-node=1           # Number of tasks per node
#SBATCH --cpus-per-task=2             # Number of CPU cores per task
#SBATCH --time=0-00:01:00             # Maximum runtime (D-HH:MM:SS)

# write contents of slurm_broker_py to slurm_test_broker.py
cat <<'EOF' > slurm_test_broker.py
{slurm_broker_py_contents}
EOF

# start the slurm_broker
python3 slurm_test_broker.py /tmp/slurm.sock &
sleep 2  # wait for the broker to start

# run squeue command from the singularity container to test the broker
echo $(singularity exec --env UNIX_SOCKET_PATH=/tmp/slurm.sock {singularity_container_image} squeue --help)

echo "Hello, world! to stdout"
""")



@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_singularity_slurm_remote(ssh_service: SSHService, slurm_service_remote: SlurmServiceRemoteHPC) -> None:
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # 1. Create a singularity definition file
        singularity_def_file = tmpdir / "slurm_test.def"
        with open(singularity_def_file, "w") as f:
            f.write(singularity_def_contents)
        # Build the singularity image remotely using ssh
        await ssh_service.scp_upload(local_file=singularity_def_file, remote_path=Path("slurm_test.def"))
        await ssh_service.run_command(
            command=f"ssh mantis-039 singularity build --ignore-fakeroot-command --force {singularity_container_image} slurm_test.def"
        )

        # write the sbatch file to a temporary file
        sbatch_file = tmpdir / "slurm_test.sbatch"
        with open(sbatch_file, "w") as f:
            f.write(sbatch_file_contents)

        # 2. Submit the job
        slurmjobid = await slurm_service_remote.submit_job(
            local_sbatch_file=sbatch_file, remote_sbatch_file=Path("slurm_test.sbatch")
        )
        # sleep for a few seconds to allow the job to be scheduled
        # await asyncio.sleep(5)

        # 5. Wait for the job to finish
        slurm_job: SlurmJob | None = None
        for _ in range(60):
            slurm_job = await slurm_service_remote.get_job_status(slurmjobid=slurmjobid)
            print(slurm_job)
            if not slurm_job or slurm_job.job_state in ("COMPLETED", "FAILED", "CANCELLED"):
                break
            time.sleep(1)

        assert slurm_job
        assert slurm_job.job_id == slurmjobid
        assert slurm_job.job_state == "COMPLETED", (
            f"Job {slurmjobid} did not complete successfully, state: {slurm_job.job_state}"
        )

        # 6. Check the output
        output_file = tmpdir / "slurm_test.out"
        await ssh_service.scp_download(local_file=output_file, remote_path=Path("slurm_test.out"))

        assert output_file.exists()
        with open(output_file) as f:
            output_content = f.read()

        assert "Usage: squeue" in output_content, "Output file does not contain expected content"



@pytest.mark.skipif(not get_settings().hpc_has_local_slurm, reason="local slurm not available (HPC_HAS_LOCAL_SLURM=False)")
@pytest.mark.skipif(not get_settings().hpc_has_local_singularity, reason="local singularity not available (HPC_HAS_LOCAL_SINGULARITY=False)")
@pytest.mark.skipif(not get_settings().hpc_has_local_volume, reason="local hpc volume not available (HPC_HAS_LOCAL_VOLUME=False)")
@pytest.mark.asyncio
async def test_singularity_slurm_local(slurm_service_local: SlurmServiceLocalHPC) -> None:
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = Path(tmpdir_str)

        # 1. Create a singularity definition file
        singularity_def_file = tmpdir / "slurm_test.def"
        with open(singularity_def_file, "w") as f:
            f.write(singularity_def_contents)

        # Build the singularity image locally
        build_command = f"{get_settings().singularity_local_command} build --ignore-fakeroot-command --force {singularity_container_image} {singularity_def_file}"
        proc = await asyncio.create_subprocess_shell(
            build_command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to build singularity image: {stderr.decode()}")

        # write the sbatch file to a temporary file
        sbatch_file = tmpdir / "slurm_test.sbatch"
        with open(sbatch_file, "w") as f:
            f.write(sbatch_file_contents)

        # 2. Submit the job
        slurmjobid = await slurm_service_local.submit_job(
            local_sbatch_file=sbatch_file, remote_sbatch_file=Path("slurm_test.sbatch")
        )
        # sleep for a few seconds to allow the job to be scheduled
        # await asyncio.sleep(5)

        # 5. Wait for the job to finish
        slurm_job: SlurmJob | None = None
        for _ in range(60):
            slurm_job = await slurm_service_local.get_job_status(slurmjobid=slurmjobid)
            print(slurm_job)
            if not slurm_job or slurm_job.job_state in ("COMPLETED", "FAILED", "CANCELLED"):
                break
            time.sleep(1)

        assert slurm_job
        assert slurm_job.job_id == slurmjobid
        assert slurm_job.job_state == "COMPLETED", (
            f"Job {slurmjobid} did not complete successfully, state: {slurm_job.job_state}"
        )

        # 6. Check the output
        output_file = tmpdir / "slurm_test.out"
        await ssh_service.scp_download(local_file=output_file, remote_path=Path("slurm_test.out"))

        assert output_file.exists()
        with open(output_file) as f:
            output_content = f.read()

        assert "Usage: squeue" in output_content, "Output file does not contain expected content"
