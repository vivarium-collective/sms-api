"""Nextflow Service Integration Tests.

These tests verify the NextflowServiceSlurm class which provides a production
implementation of Nextflow workflow execution via SLURM.

The NextflowServiceSlurm.run_simulation method is designed to be the production
implementation of the workflow tested in test_nextflow_workflow_sms_ccam_slurm_executor.

Run with: uv run pytest tests/integration/test_nextflow_service.py -v

Prerequisites:
- SSH access to HPC (SLURM_SUBMIT_KEY_PATH configured)
- Write access to HPC paths
- Rebuilt container with Cython extensions (vecoli-8f119dd.sif)

Known Issues:
- vEcoli NegativeCountsError: The real simulation crashes due to a model bug
  in ecoli/processes/allocator.py. The infrastructure works correctly.
"""

import pytest

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.simulation.nextflow_service import NextflowServiceSlurm

# Skip all tests if SSH not configured
pytestmark = pytest.mark.skipif(
    len(get_settings().slurm_submit_key_path) == 0,
    reason="slurm ssh key file not supplied",
)


@pytest.mark.asyncio
async def test_nextflow_service_run_simulation(
    nextflow_service_slurm: NextflowServiceSlurm,
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    sms_ccam_main_real_nf: str,
    sms_ccam_workflow_config_real: str,
    nextflow_config_sms_ccam_real: str,
    slurm_template_nextflow_sms_ccam_real: str,
) -> None:
    """Test NextflowServiceSlurm.run_simulation with real simulation workflow.

    This test verifies the production implementation of Nextflow workflow execution:
    - Creates remote output directories
    - Uploads workflow files (main.nf, workflow_config.json, nextflow.config)
    - Submits SLURM job
    - Polls for job completion
    - Verifies output files were created

    Note: This test is currently skipped due to vEcoli NegativeCountsError model bug.
    The simulation crashes with a numerical precision issue in the allocator process.

    The infrastructure works correctly:
    - Container Python environment loads correctly
    - Cython extensions are available
    - createVariants process completes successfully
    - sim_gen_1 process starts and begins simulation
    """
    outputs = await nextflow_service_slurm.run_simulation(
        slurm_service=slurm_service,
        sms_ccam_main_real_nf=sms_ccam_main_real_nf,
        sms_ccam_workflow_config_real=sms_ccam_workflow_config_real,
        nextflow_config_sms_ccam_real=nextflow_config_sms_ccam_real,
        slurm_template_nextflow_sms_ccam_real=slurm_template_nextflow_sms_ccam_real,
    )

    assert len(outputs) > 0, "Expected at least one output file from simulation"


@pytest.mark.asyncio
async def test_nextflow_service_submit_job(
    nextflow_service_slurm: NextflowServiceSlurm,
    slurm_service: SlurmService,
    ssh_session_service: SSHSessionService,
    sms_ccam_main_real_nf: str,
    sms_ccam_workflow_config_real: str,
    nextflow_config_sms_ccam_real: str,
    slurm_template_nextflow_sms_ccam_real: str,
) -> None:
    """Test NextflowServiceSlurm.submit_simulation_job.

    This test verifies that the service correctly:
    1. Creates remote directories
    2. Uploads workflow files
    3. Submits the SLURM job
    4. Returns a valid NextflowJobSubmission
    """
    from sms_api.dependencies import get_ssh_session_service

    async with get_ssh_session_service().session() as ssh:
        submission = await nextflow_service_slurm.submit_simulation_job(
            slurm_service=slurm_service,
            ssh=ssh,
            sms_ccam_main_real_nf=sms_ccam_main_real_nf,
            sms_ccam_workflow_config_real=sms_ccam_workflow_config_real,
            nextflow_config_sms_ccam_real=nextflow_config_sms_ccam_real,
            slurm_template_nextflow_sms_ccam_real=slurm_template_nextflow_sms_ccam_real,
        )

        assert submission.job_id > 0, f"Expected valid job ID, got {submission.job_id}"
        assert submission.remote_output_file is not None
        assert submission.remote_error_file is not None
        assert submission.simulation_output_dir is not None


@pytest.mark.asyncio
async def test_nextflow_service_instantiation(
    nextflow_service_slurm: NextflowServiceSlurm,
) -> None:
    """Test that NextflowServiceSlurm can be instantiated.

    This simple test verifies the service class is properly defined and
    can be instantiated without errors.
    """
    assert nextflow_service_slurm is not None
    assert isinstance(nextflow_service_slurm, NextflowServiceSlurm)
    assert hasattr(nextflow_service_slurm, "run_simulation")
    assert hasattr(nextflow_service_slurm, "submit_simulation_job")
    assert hasattr(nextflow_service_slurm, "poll_simulation_job")
    assert hasattr(nextflow_service_slurm, "list_simulation_outputs")
