from collections.abc import AsyncGenerator
from pathlib import Path
from textwrap import dedent

import pytest
import pytest_asyncio

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings


@pytest_asyncio.fixture(scope="session")
async def ssh_service() -> AsyncGenerator[SSHService]:
    settings = get_settings()
    ssh_service = SSHService(
        hostname=settings.slurm_submit_host,
        username=settings.slurm_submit_user,
        key_path=Path(settings.slurm_submit_key_path),
        known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
    )
    yield ssh_service
    await ssh_service.close()


@pytest_asyncio.fixture(scope="session")
async def slurm_service(ssh_service: SSHService) -> AsyncGenerator[SlurmService]:
    # saved_ssh_service = get_ssh_service()
    slurm_service = SlurmService(ssh_service=ssh_service)
    yield slurm_service
    # set_ssh_service(saved_ssh_service)
    # slurm_service.close()  # nothing to close, ssh_session is closed in ssh_service.close()


@pytest.fixture(scope="session")
def slurm_template_hello_TEMPLATE() -> str:
    settings = get_settings()
    partition = settings.slurm_partition
    qos = settings.slurm_qos
    template = dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name=my_test_job        # Job name
        # SBATCH --chdir=workDirname_1         # Working directory
        #SBATCH --output=output.txt           # Standard output file
        #SBATCH --error=error.txt             # Standard error file
        #SBATCH --partition={partition}       # Partition or queue name
        #SBATCH --qos={qos}                   # QOS level
        #SBATCH --nodes=1                     # Number of nodes
        #SBATCH --ntasks-per-node=1           # Number of tasks per node
        #SBATCH --cpus-per-task=1             # Number of CPU cores per task
        #SBATCH --time=0-00:01:00             # Maximum runtime (D-HH:MM:SS)

        #Load necessary modules (if needed)
        #module load module_name

        #Your job commands go here
        #For example:
        #python my_script.py

        #Optionally, you can include cleanup commands here (e.g., after the job finishes)
        #For example:
        #rm some_temp_file.txt
        echo "Hello, world! to stdout"
        sleep SLEEP_TIME
        echo "Hello, world! to file" > hello.txt
        """)
    return template


@pytest.fixture(scope="session")
def slurm_template_hello_1s(slurm_template_hello_TEMPLATE: str) -> str:
    template = slurm_template_hello_TEMPLATE
    template = template.replace("SLEEP_TIME", "1")
    return template


@pytest.fixture(scope="session")
def slurm_template_hello_10s(slurm_template_hello_TEMPLATE: str) -> str:
    template = slurm_template_hello_TEMPLATE
    template = template.replace("SLEEP_TIME", "10")
    return template
