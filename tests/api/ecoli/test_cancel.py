"""Tests for simulation cancel flow.

Run with: uv run pytest tests/api/ecoli/test_cancel.py -v
"""

import pytest

from sms_api.common.hpc.job_service import JobStatusUpdate
from sms_api.common.models import JobStatus
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import (
    JobType,
    SimulationRequest,
)


@pytest.mark.asyncio
async def test_cancel_running_simulation(
    experiment_request: SimulationRequest,
    database_service: DatabaseServiceSQL,
) -> None:
    """Test cancelling a running simulation updates status to CANCELLED."""
    simulation = await database_service.insert_simulation(sim_request=experiment_request)
    hpcrun = await database_service.insert_hpcrun(
        external_job_id="12345",
        job_backend="slurm",
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id="test-correlation",
    )
    assert hpcrun.status == JobStatus.RUNNING

    # Cancel it
    update = JobStatusUpdate(job_id="12345", status=JobStatus.CANCELLED)
    await database_service.update_hpcrun_status(hpcrun_id=hpcrun.database_id, update=update)

    # Verify
    updated = await database_service.get_hpcrun_by_ref(ref_id=simulation.database_id, job_type=JobType.SIMULATION)
    assert updated is not None
    assert updated.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_with_error_message(
    experiment_request: SimulationRequest,
    database_service: DatabaseServiceSQL,
) -> None:
    """Test that cancel can record an error message."""
    simulation = await database_service.insert_simulation(sim_request=experiment_request)
    hpcrun = await database_service.insert_hpcrun(
        external_job_id="12345",
        job_backend="slurm",
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id="test-correlation",
    )

    update = JobStatusUpdate(
        job_id="12345",
        status=JobStatus.CANCELLED,
        error_message="Cancelled by user",
    )
    await database_service.update_hpcrun_status(hpcrun_id=hpcrun.database_id, update=update)

    updated = await database_service.get_hpcrun_by_ref(ref_id=simulation.database_id, job_type=JobType.SIMULATION)
    assert updated is not None
    assert updated.status == JobStatus.CANCELLED
    assert updated.error_message == "Cancelled by user"


@pytest.mark.asyncio
async def test_cancel_already_completed_is_noop(
    experiment_request: SimulationRequest,
    database_service: DatabaseServiceSQL,
) -> None:
    """Test that the cancel handler returns existing status for terminal jobs."""
    from sms_api.common.handlers.simulations import cancel_simulation
    from tests.fixtures.simulation_service_mocks import ConcreteSimulationService

    simulation = await database_service.insert_simulation(sim_request=experiment_request)
    hpcrun = await database_service.insert_hpcrun(
        external_job_id="12345",
        job_backend="slurm",
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id="test-correlation",
    )

    # Mark as completed
    update = JobStatusUpdate(job_id="12345", status=JobStatus.COMPLETED)
    await database_service.update_hpcrun_status(hpcrun_id=hpcrun.database_id, update=update)

    # Cancel should return COMPLETED without calling cancel_job
    mock_service = ConcreteSimulationService()
    result = await cancel_simulation(
        db_service=database_service,
        simulation_service=mock_service,
        simulation_id=simulation.database_id,
    )
    assert result.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_hpcrun_external_job_id_slurm(
    experiment_request: SimulationRequest,
    database_service: DatabaseServiceSQL,
) -> None:
    """Test that external_job_id returns SLURM job ID as string."""
    simulation = await database_service.insert_simulation(sim_request=experiment_request)
    hpcrun = await database_service.insert_hpcrun(
        external_job_id="99999",
        job_backend="slurm",
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id="test-correlation",
    )
    assert hpcrun.external_job_id == "99999"
    assert hpcrun.slurmjobid == 99999
    assert hpcrun.job_backend == "slurm"


@pytest.mark.asyncio
async def test_hpcrun_external_job_id_k8s(
    experiment_request: SimulationRequest,
    database_service: DatabaseServiceSQL,
) -> None:
    """Test that external_job_id returns K8s job name."""
    simulation = await database_service.insert_simulation(sim_request=experiment_request)
    hpcrun = await database_service.insert_hpcrun(
        external_job_id="nf-sim-abc1234",
        job_backend="k8s",
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id="test-correlation",
    )
    assert hpcrun.external_job_id == "nf-sim-abc1234"
    assert hpcrun.k8s_job_name == "nf-sim-abc1234"
    assert hpcrun.slurmjobid is None
    assert hpcrun.job_backend == "k8s"
