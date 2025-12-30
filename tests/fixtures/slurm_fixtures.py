from collections.abc import AsyncGenerator
from pathlib import Path
from textwrap import dedent

import pytest
import pytest_asyncio

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings


@pytest_asyncio.fixture(scope="session")
async def ssh_session_service() -> AsyncGenerator[SSHSessionService]:
    from sms_api.dependencies import set_ssh_session_service

    settings = get_settings()
    ssh_session_service = SSHSessionService(
        hostname=settings.slurm_submit_host,
        username=settings.slurm_submit_user,
        key_path=Path(settings.slurm_submit_key_path),
        known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
    )
    # Set the singleton so it's available throughout the test session
    set_ssh_session_service(ssh_session_service)
    yield ssh_session_service
    # Clean up the singleton at end of session
    set_ssh_session_service(None)


@pytest_asyncio.fixture(scope="session")
async def slurm_service(ssh_session_service: SSHSessionService) -> AsyncGenerator[SlurmService]:
    # ssh_session_service fixture ensures the singleton is already set
    slurm_service = SlurmService()
    yield slurm_service


@pytest.fixture(scope="session")
def slurm_template_hello_TEMPLATE() -> str:
    settings = get_settings()
    partition = settings.slurm_partition
    qos_clause = f"#SBATCH --qos={settings.slurm_qos}" if settings.slurm_qos else ""
    template = dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name=my_test_job        # Job name
        # SBATCH --chdir=workDirname_1         # Working directory
        #SBATCH --output=output.txt           # Standard output file
        #SBATCH --error=error.txt             # Standard error file
        #SBATCH --partition={partition}       # Partition or queue name
        {qos_clause}
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


@pytest.fixture(scope="session")
def slurm_template_with_storage() -> str:
    """
    Slurm template that tests S3-compatible storage download and upload functionality.
    Works with both AWS S3 and Qumulo S3-compatible storage.

    This template:
    1. Sources the s3_helpers.sh script
    2. Downloads a test file from S3-compatible storage
    3. Processes it (adds a timestamp)
    4. Uploads the result to the same S3-compatible storage

    The storage provider is determined by STORAGE_TYPE environment variable:
    - "aws" (default): Standard AWS S3
    - "qumulo": Qumulo S3-compatible storage with special handling
    """
    settings = get_settings()
    partition = settings.slurm_partition
    qos_clause = f"#SBATCH --qos={get_settings().slurm_qos}" if get_settings().slurm_qos else ""
    template = dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name=storage_test_job   # Job name
        #SBATCH --output=storage_test.out     # Standard output file
        #SBATCH --error=storage_test.err      # Standard error file
        #SBATCH --partition={partition}       # Partition or queue name
        {qos_clause}
        #SBATCH --nodes=1                     # Number of nodes
        #SBATCH --ntasks-per-node=1           # Number of tasks per node
        #SBATCH --cpus-per-task=1             # Number of CPU cores per task
        #SBATCH --time=0-00:05:00             # Maximum runtime (D-HH:MM:SS)

        set -e  # Exit on error
        set -x  # Print commands

        echo "=== Storage Test Job Starting ==="
        echo "Job ID: $SLURM_JOB_ID"
        echo "Node: $SLURM_NODELIST"
        echo "Working directory: $(pwd)"

        # Source the helper functions
        echo "=== Sourcing s3_helpers.sh ==="
        if [ -f "HELPERS_PATH" ]; then
            source HELPERS_PATH
        else
            echo "Error: s3_helpers.sh not found" >&2
            exit 1
        fi

        # Test environment variables
        echo "=== Checking environment variables ==="
        echo "STORAGE_TYPE: ${{STORAGE_TYPE:-aws}}"
        echo "STORAGE_BUCKET: ${{STORAGE_BUCKET:-NOT SET}}"
        echo "STORAGE_ENDPOINT_URL: ${{STORAGE_ENDPOINT_URL:-NOT SET}}"
        echo "STORAGE_VERIFY_SSL: ${{STORAGE_VERIFY_SSL:-true}}"
        echo "AWS_ACCESS_KEY_ID: ${{AWS_ACCESS_KEY_ID:0:10}}..." # Only show first 10 chars

        # Download test file from S3
        echo "=== Downloading test file from storage ==="
        s3_download "INPUT_KEY" "input_file.txt"

        # Verify download
        if [ ! -f "input_file.txt" ]; then
            echo "Error: Downloaded file not found" >&2
            exit 1
        fi
        echo "Downloaded file contents:"
        cat input_file.txt

        # Process the file (add timestamp)
        echo "=== Processing file ==="
        echo "Processed at $(date)" > processed_file.txt
        cat input_file.txt >> processed_file.txt
        echo "Job ID: $SLURM_JOB_ID" >> processed_file.txt

        echo "Processed file contents:"
        cat processed_file.txt

        # Upload result to storage
        echo "=== Uploading result to storage ==="
        s3_upload "processed_file.txt" "OUTPUT_KEY"

        echo "=== Storage Test Job Completed Successfully ==="
        """)
    return template


@pytest.fixture(scope="session")
def nextflow_script_hello() -> str:
    """
    Simple Nextflow workflow that runs a Python script to verify Nextflow
    is properly configured on the remote Slurm cluster.

    The workflow:
    1. Runs a Python process that prints a greeting and writes to a file
    2. Verifies the output in a second process
    """
    script = dedent("""\
        #!/usr/bin/env nextflow

        nextflow.enable.dsl=2

        process sayHello {
            output:
            path 'hello.txt'

            script:
            '''
            python3 -c "
import datetime
message = f'Hello from Nextflow at {datetime.datetime.now().isoformat()}'
print(message)
with open('hello.txt', 'w') as f:
    f.write(message + chr(10))
    f.write('Nextflow Python integration test passed' + chr(10))
"
            '''
        }

        process verifyOutput {
            input:
            path hello_file

            output:
            path 'result.txt'

            script:
            '''
            python3 -c "
with open('hello.txt', 'r') as f:
    content = f.read()
assert 'Hello from Nextflow' in content, 'Expected greeting not found'
assert 'test passed' in content, 'Expected test message not found'
with open('result.txt', 'w') as f:
    f.write('VERIFICATION_SUCCESS' + chr(10))
    f.write(content)
print('Verification completed successfully')
"
            '''
        }

        workflow {
            sayHello()
            verifyOutput(sayHello.out)
        }
        """)
    return script


@pytest.fixture(scope="session")
def slurm_template_nextflow() -> str:
    """
    Slurm sbatch template for running a Nextflow workflow.

    This template:
    1. Copies the Nextflow script to the work directory
    2. Runs Nextflow with the local executor (processes run on same node)
    3. Captures exit status
    """
    settings = get_settings()
    partition = settings.slurm_partition
    qos_clause = f"#SBATCH --qos={settings.slurm_qos}" if settings.slurm_qos else ""
    nodelist_clause = f"#SBATCH --nodelist={settings.slurm_node_list}" if settings.slurm_node_list else ""
    template = dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name=nextflow_test      # Job name
        #SBATCH --output=REMOTE_LOG_OUTPUT_FILE    # Standard output file
        #SBATCH --error=REMOTE_LOG_ERROR_FILE      # Standard error file
        #SBATCH --partition={partition}       # Partition or queue name
        {qos_clause}
        {nodelist_clause}
        #SBATCH --nodes=1                     # Number of nodes
        #SBATCH --ntasks-per-node=1           # Number of tasks per node
        #SBATCH --cpus-per-task=2             # Number of CPU cores per task
        #SBATCH --time=0-00:10:00             # Maximum runtime (D-HH:MM:SS)

        set -e  # Exit on error

        echo "=== Nextflow Test Job Starting ==="
        echo "Job ID: $SLURM_JOB_ID"
        echo "Node: $SLURM_NODELIST"
        echo "Working directory: $(pwd)"

        # Initialize module system if available
        if [ -f /etc/profile.d/modules.sh ]; then
            source /etc/profile.d/modules.sh
        elif [ -f /usr/share/Modules/init/bash ]; then
            source /usr/share/Modules/init/bash
        fi

        # Check Java is available (required by Nextflow)
        echo "=== Checking Java installation ==="
        if ! command -v java &> /dev/null && [ -z "$JAVA_HOME" ]; then
            echo "Java not found, attempting to load java module..."
            if command -v module &> /dev/null; then
                module load java || {{ echo "ERROR: Failed to load java module"; exit 1; }}
            else
                echo "ERROR: Neither java nor module system available"
                exit 1
            fi
        fi
        java -version

        # Check Nextflow is available
        echo "=== Checking Nextflow installation ==="
        which nextflow || {{ echo "ERROR: nextflow not found in PATH"; exit 1; }}
        nextflow -version

        # Check Python is available
        echo "=== Checking Python installation ==="
        which python3 || {{ echo "ERROR: python3 not found in PATH"; exit 1; }}
        python3 --version

        # The Nextflow script should be uploaded alongside this sbatch file
        NF_SCRIPT="NEXTFLOW_SCRIPT_PATH"

        if [ ! -f "$NF_SCRIPT" ]; then
            echo "ERROR: Nextflow script not found: $NF_SCRIPT"
            exit 1
        fi

        echo "=== Running Nextflow workflow ==="
        echo "Script: $NF_SCRIPT"

        # Run Nextflow with local executor
        nextflow run "$NF_SCRIPT" -with-report REMOTE_REPORT_FILE -with-trace REMOTE_TRACE_FILE

        NF_EXIT_CODE=$?

        echo "=== Nextflow completed with exit code: $NF_EXIT_CODE ==="

        # Check for success marker
        if [ -f "work/*/*/result.txt" ]; then
            echo "=== Verification result ==="
            cat work/*/*/result.txt
        fi

        exit $NF_EXIT_CODE
        """)
    return template
