from collections.abc import AsyncGenerator
from pathlib import Path
from textwrap import dedent

import pytest
import pytest_asyncio

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.simulation.nextflow_service import NextflowServiceSlurm


def _build_nextflow_sbatch_template(
    *,
    job_name: str,
    cpus_per_task: int = 1,
    time_limit: str = "0-00:10:00",
) -> str:
    """
    Build a Slurm sbatch template for running Nextflow workflows.

    Args:
        job_name: Slurm job name
        cpus_per_task: Number of CPU cores for the parent job
        time_limit: Maximum runtime in D-HH:MM:SS format

    Returns:
        Sbatch template string with placeholders for paths
    """
    settings = get_settings()
    partition = settings.slurm_partition
    qos_clause = f"#SBATCH --qos={settings.slurm_qos}" if settings.slurm_qos else ""
    nodelist_clause = f"#SBATCH --nodelist={settings.slurm_node_list}" if settings.slurm_node_list else ""

    return f"""#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --output=REMOTE_LOG_OUTPUT_FILE
#SBATCH --error=REMOTE_LOG_ERROR_FILE
#SBATCH --partition={partition}
{qos_clause}
{nodelist_clause}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task={cpus_per_task}
#SBATCH --time={time_limit}

set -e

echo "=== Nextflow Job Starting ==="
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

# The Nextflow script and config should be uploaded alongside this sbatch file
NF_SCRIPT="NEXTFLOW_SCRIPT_PATH"
NF_CONFIG="NEXTFLOW_CONFIG_PATH"

if [ ! -f "$NF_SCRIPT" ]; then
    echo "ERROR: Nextflow script not found: $NF_SCRIPT"
    exit 1
fi

if [ ! -f "$NF_CONFIG" ]; then
    echo "ERROR: Nextflow config not found: $NF_CONFIG"
    exit 1
fi

echo "=== Nextflow Configuration ==="
cat "$NF_CONFIG"

echo "=== Starting weblog receiver ==="
export EVENTS_FILE="REMOTE_EVENTS_FILE"

# Start weblog receiver in background on a dynamic port
python3 << 'WEBLOG_SCRIPT' &
{WEBLOG_RECEIVER_SCRIPT}WEBLOG_SCRIPT

WEBLOG_PID=$!
sleep 1

# Read the port from temp file
WEBLOG_PORT=$(cat /tmp/weblog_port_$$ 2>/dev/null || echo "9999")
rm -f /tmp/weblog_port_$$
echo "Weblog receiver running on port $WEBLOG_PORT (PID: $WEBLOG_PID)"

echo "=== Running Nextflow workflow ==="
echo "Script: $NF_SCRIPT"
echo "Config: $NF_CONFIG"

# Run Nextflow with config and weblog
nextflow run "$NF_SCRIPT" \\
    -c "$NF_CONFIG" \\
    -with-report REMOTE_REPORT_FILE \\
    -with-trace REMOTE_TRACE_FILE \\
    -with-weblog http://localhost:$WEBLOG_PORT

NF_EXIT_CODE=$?

# Cleanup weblog receiver (use || true to prevent set -e from failing)
kill $WEBLOG_PID 2>/dev/null || true
wait $WEBLOG_PID 2>/dev/null || true

echo "=== Nextflow completed with exit code: $NF_EXIT_CODE ==="

exit $NF_EXIT_CODE
"""


# Weblog receiver script - used by Nextflow sbatch templates to capture weblog events
WEBLOG_RECEIVER_SCRIPT = """import json
import os
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler

EVENTS_FILE = os.environ.get('EVENTS_FILE', 'events.ndjson')

class WeblogHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        data = self.rfile.read(length)
        try:
            event = json.loads(data.decode())
            with open(EVENTS_FILE, 'a') as f:
                f.write(json.dumps(event) + chr(10))
        except Exception as ex:
            print("Error processing event:", ex)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('localhost', 0))
port = sock.getsockname()[1]
sock.close()

with open('/tmp/weblog_port_' + str(os.getppid()), 'w') as f:
    f.write(str(port))

print("Weblog receiver starting on port", port, "writing to", EVENTS_FILE)
HTTPServer(('localhost', port), WeblogHandler).serve_forever()
"""


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
    """Slurm sbatch template for running Nextflow with local executor."""
    return _build_nextflow_sbatch_template(
        job_name="nextflow_test",
        cpus_per_task=2,
        time_limit="0-00:10:00",
    )


@pytest.fixture(scope="session")
def nextflow_config_slurm_executor() -> str:
    """
    Nextflow configuration file that uses Slurm as the executor.

    This configures Nextflow to submit each process as a separate Slurm job
    instead of running them locally on the same node.
    """
    settings = get_settings()
    partition = settings.slurm_partition
    qos_line = f"    qos = '{settings.slurm_qos}'" if settings.slurm_qos else ""
    clusterOptions_line = (
        f"    clusterOptions = '--nodelist={settings.slurm_node_list}'" if settings.slurm_node_list else ""
    )

    config = f"""
// Nextflow configuration for Slurm executor
process {{
    executor = 'slurm'
    queue = '{partition}'
{qos_line}
{clusterOptions_line}
    time = '5m'
    cpus = 1
    memory = '512 MB'
}}

// Disable container by default (processes run natively)
docker.enabled = false
singularity.enabled = false

// Work directory configuration
workDir = 'WORK_DIR_PLACEHOLDER'
"""
    return config


@pytest.fixture(scope="session")
def nextflow_config_local_executor() -> str:
    """
    Nextflow configuration file that uses the local executor.

    This configures Nextflow to run processes locally on the same node,
    with a unique work directory per run.
    """
    config = """
// Nextflow configuration for local executor
process {
    executor = 'local'
}

// Disable container by default (processes run natively)
docker.enabled = false
singularity.enabled = false

// Work directory configuration (unique per run)
workDir = 'WORK_DIR_PLACEHOLDER'
"""
    return config


@pytest.fixture(scope="session")
def nextflow_script_hello_slurm() -> str:
    """
    Nextflow workflow for Slurm executor testing.

    Similar to nextflow_script_hello but with explicit resource requirements
    that work well with Slurm scheduling.
    """
    script = dedent("""\
        #!/usr/bin/env nextflow

        nextflow.enable.dsl=2

        process sayHello {
            // Resources for Slurm scheduling
            cpus 1
            memory '256 MB'
            time '2m'

            output:
            path 'hello.txt'

            script:
            '''
            python3 -c "
import datetime
import os
message = f'Hello from Nextflow Slurm job'
slurm_job_id = os.environ.get('SLURM_JOB_ID', 'unknown')
print(f'{message} (SLURM_JOB_ID={slurm_job_id})')
with open('hello.txt', 'w') as f:
    f.write(message + chr(10))
    f.write(f'SLURM_JOB_ID={slurm_job_id}' + chr(10))
    f.write(f'Timestamp: {datetime.datetime.now().isoformat()}' + chr(10))
    f.write('Nextflow Slurm executor test passed' + chr(10))
"
            '''
        }

        process verifyOutput {
            // Resources for Slurm scheduling
            cpus 1
            memory '256 MB'
            time '2m'

            input:
            path hello_file

            output:
            path 'result.txt'

            script:
            '''
            python3 -c "
import os
slurm_job_id = os.environ.get('SLURM_JOB_ID', 'unknown')
print(f'Verify process running as SLURM_JOB_ID={slurm_job_id}')
with open('hello.txt', 'r') as f:
    content = f.read()
assert 'Hello from Nextflow' in content, 'Expected greeting not found'
assert 'test passed' in content, 'Expected test message not found'
with open('result.txt', 'w') as f:
    f.write('VERIFICATION_SUCCESS' + chr(10))
    f.write(f'Verified by SLURM_JOB_ID={slurm_job_id}' + chr(10))
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
def slurm_template_nextflow_slurm_executor() -> str:
    """Slurm sbatch template for running Nextflow with Slurm executor."""
    return _build_nextflow_sbatch_template(
        job_name="nextflow_slurm_test",
        cpus_per_task=1,
        time_limit="0-00:15:00",
    )


# =============================================================================
# SMS CCAM Nextflow Workflow Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def nextflow_inputs_dir() -> Path:
    """Path to the nextflow_inputs fixture directory."""
    return Path(__file__).parent / "nextflow_inputs"


@pytest.fixture(scope="session")
def sms_ccam_main_nf(nextflow_inputs_dir: Path) -> str:
    """Load the main.nf workflow file from fixtures."""
    main_nf_path = nextflow_inputs_dir / "main.nf"
    return main_nf_path.read_text()


@pytest.fixture(scope="session")
def sms_ccam_main_stub_nf(nextflow_inputs_dir: Path) -> str:
    """Load the self-contained main_stub.nf workflow file for stub testing.

    This version replaces external includes with local process definitions
    that have stub blocks, allowing the workflow to run in -stub mode without
    depending on external vEcoli modules.
    """
    main_stub_nf_path = nextflow_inputs_dir / "main_stub.nf"
    return main_stub_nf_path.read_text()


@pytest.fixture(scope="session")
def sms_ccam_workflow_config(nextflow_inputs_dir: Path) -> str:
    """Load the workflow_config.json from fixtures."""
    config_path = nextflow_inputs_dir / "workflow_config.json"
    return config_path.read_text()


@pytest.fixture(scope="session")
def sms_ccam_nextflow_config(nextflow_inputs_dir: Path) -> str:
    """Load the nextflow.config from fixtures."""
    config_path = nextflow_inputs_dir / "nextflow.config"
    return config_path.read_text()


@pytest.fixture(scope="session")
def slurm_template_nextflow_sms_ccam() -> str:
    """Slurm sbatch template for running the SMS CCAM Nextflow workflow with stub mode."""
    return _build_nextflow_sbatch_template(
        job_name="nextflow_sms_ccam_test",
        cpus_per_task=2,
        time_limit="0-00:30:00",
    )


@pytest.fixture(scope="session")
def sms_ccam_main_real_nf(nextflow_inputs_dir: Path) -> str:
    """Load the main_real.nf workflow file for real simulation testing.

    This version uses the actual vEcoli simulation modules and produces
    parquet output. It runs a minimal simulation for integration testing.
    """
    main_real_nf_path = nextflow_inputs_dir / "main_real.nf"
    return main_real_nf_path.read_text()


@pytest.fixture(scope="session")
def sms_ccam_workflow_config_real(nextflow_inputs_dir: Path) -> str:
    """Load the minimal workflow_config_real.json for real simulation testing.

    This config:
    - Uses existing parca dataset (skips running parca)
    - Uses parquet emitter for output
    - Minimal processes and short duration (120s)
    - Single seed, single generation
    """
    config_path = nextflow_inputs_dir / "workflow_config_real.json"
    return config_path.read_text()


@pytest.fixture(scope="session")
def slurm_template_nextflow_sms_ccam_real() -> str:
    """Slurm sbatch template for running real SMS CCAM simulations.

    Uses longer time limits since real simulations take more time than stubs.
    """
    return _build_nextflow_sbatch_template(
        job_name="nextflow_sms_ccam_real",
        cpus_per_task=2,
        time_limit="0-02:00:00",  # 2 hours for real simulation
    )


@pytest.fixture(scope="session")
def nextflow_config_sms_ccam_real() -> str:
    """
    Nextflow configuration for real SMS CCAM simulation with Singularity container.

    This config:
    - Uses SLURM executor for process jobs
    - Enables Singularity for containerized execution
    - Points to the vEcoli container image
    - Uses hpc_sim_base_path for output
    """
    settings = get_settings()
    partition = settings.slurm_partition
    qos_line = f"    qos = '{settings.slurm_qos}'" if settings.slurm_qos else ""
    clusterOptions_line = (
        f"    clusterOptions = '--nodelist={settings.slurm_node_list}'" if settings.slurm_node_list else ""
    )

    config = f"""
// Global params for SMS CCAM real simulation test
params {{
    experimentId = 'EXPERIMENT_ID_PLACEHOLDER'
    config = 'WORKFLOW_CONFIG_PATH'
    sim_data_path = 'SIM_DATA_PATH_PLACEHOLDER'
    lineage_seed = 0
    parca_cpus = 2
    publishDir = 'PUBLISH_DIR_PLACEHOLDER'
    container_image = 'CONTAINER_IMAGE_PLACEHOLDER'
    hyperqueue = false
    projectRoot = '/vEcoli'
}}

trace.enabled = true
trace.raw = true

profiles {{
    ccam_real {{
        process {{
            executor = 'slurm'
            queue = '{partition}'
{qos_line}
{clusterOptions_line}
            container = params.container_image
            // Use pre-installed venv directly to avoid editable install issues
            // PATH includes .venv/bin and the UV-installed Python so 'python' resolves correctly
            // PYTHONPATH includes /vEcoli for module imports
            containerOptions = '--writable-tmpfs --bind /projects/SMS:/projects/SMS --bind /tmp:/tmp --env PATH=/vEcoli/.venv/bin:/vEcoli/.uv_python/cpython-3.12.9-linux-x86_64-gnu/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin --env PYTHONPATH=/vEcoli'
            cpus = 1
            memory = '4 GB'
            time = '30m'
            errorStrategy = 'retry'
            maxRetries = 2
        }}
        singularity.enabled = true
        singularity.autoMounts = true
        docker.enabled = false
        params.projectRoot = '/vEcoli'
        // Set PATH and PYTHONPATH for the container environment
        env.PATH = '/vEcoli/.venv/bin:/vEcoli/.uv_python/cpython-3.12.9-linux-x86_64-gnu/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        env.PYTHONPATH = '/vEcoli'
    }}
}}

// Work directory configuration
workDir = 'WORK_DIR_PLACEHOLDER'
"""
    return config


@pytest.fixture(scope="session")
def nextflow_config_sms_ccam_executor() -> str:
    """
    Nextflow configuration for SMS CCAM workflow test using SLURM executor.

    This is a simplified config that:
    - Uses the standard profile (local executor) for stub mode testing
    - Configures appropriate work directory
    - Disables containers since we're running stubs
    """
    settings = get_settings()
    partition = settings.slurm_partition
    qos_line = f"    qos = '{settings.slurm_qos}'" if settings.slurm_qos else ""
    clusterOptions_line = (
        f"    clusterOptions = '--nodelist={settings.slurm_node_list}'" if settings.slurm_node_list else ""
    )

    config = f"""
// Global default params for SMS CCAM test
params {{
    experimentId = 'sms_ccam_test'
    config = 'WORKFLOW_CONFIG_PATH'
    parca_cpus = 2
    publishDir = 'PUBLISH_DIR_PLACEHOLDER'
    container_image = ''
    hyperqueue = false
    projectRoot = '/vEcoli'
}}

trace.enabled = true
trace.raw = true

profiles {{
    standard {{
        params.projectRoot = "${{launchDir}}"
        workflow.failOnIgnore = true
        process {{
            withLabel: parca {{
                cpus = params.parca_cpus
                memory = params.parca_cpus * 2.GB
            }}
            executor = 'local'
            errorStrategy = 'ignore'
        }}
    }}
    ccam_test {{
        process {{
            withLabel: parca {{
                cpus = params.parca_cpus
                memory = params.parca_cpus * 2.GB
                time = '10m'
            }}
            executor = 'slurm'
            queue = '{partition}'
{qos_line}
{clusterOptions_line}
            cpus = 1
            memory = '512 MB'
            time = '5m'
            errorStrategy = 'ignore'
        }}
        docker.enabled = false
        singularity.enabled = false
        params.projectRoot = '/vEcoli'
        workflow.failOnIgnore = true
    }}
}}

// Work directory configuration
workDir = 'WORK_DIR_PLACEHOLDER'
"""
    return config


# =============================================================================
# Nextflow Service Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def nextflow_service_slurm() -> NextflowServiceSlurm:
    """Provide a NextflowServiceSlurm instance for integration tests.

    This service provides the production implementation for running
    Nextflow workflows via SLURM on HPC.
    """
    from sms_api.simulation.nextflow_service import NextflowServiceSlurm

    return NextflowServiceSlurm()
