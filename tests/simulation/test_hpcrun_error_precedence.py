"""error_message is written by precedence, not last-writer-wins (observability plan D4c)."""

from __future__ import annotations

import pytest

from viva_api.common.hpc.job_service import JobStatusUpdate
from viva_api.common.models import JobId, JobStatus
from viva_api.simulation.database_service import DatabaseServiceSQL
from viva_api.simulation.models import JobType, SimulationRequest


async def _row(database_service: DatabaseServiceSQL, experiment_request: SimulationRequest) -> int:
    simulation = await database_service.insert_simulation(sim_request=experiment_request)
    hpcrun = await database_service.insert_hpcrun(
        job_id=JobId.k8s_nextflow("nf-exp-abc"),
        job_type=JobType.SIMULATION,
        ref_id=simulation.database_id,
        correlation_id="946_c233c7a_ab12cd3",
    )
    return hpcrun.database_id


@pytest.mark.asyncio
async def test_insert_derives_trace_ids_from_the_correlation_id(
    experiment_request: SimulationRequest, database_service: DatabaseServiceSQL
) -> None:
    from viva_api.common.events_env import campaign_span_id, trace_id_from_correlation

    hpcrun_id = await _row(database_service, experiment_request)
    row = await database_service.get_hpcrun(hpcrun_id)
    assert row is not None
    assert row.trace_id == trace_id_from_correlation("946_c233c7a_ab12cd3")
    assert row.campaign_span_id == campaign_span_id("946_c233c7a_ab12cd3")


@pytest.mark.asyncio
async def test_a_generic_k8s_message_never_overwrites_a_task_traceback(
    experiment_request: SimulationRequest, database_service: DatabaseServiceSQL
) -> None:
    """The scheduler captured `.command.err`; a later GET /status poll brings
    Kubernetes' "backoff limit" text. The traceback must survive."""
    hpcrun_id = await _row(database_service, experiment_request)
    await database_service.update_hpcrun_status(
        hpcrun_id,
        JobStatusUpdate(
            job_id=JobId.k8s_nextflow("nf-exp-abc"),
            status=JobStatus.FAILED,
            error_message="ValueError: boom",
            error_source="command_err",
            exit_code="1",
            attempt=1,
        ),
    )
    await database_service.update_hpcrun_status(
        hpcrun_id,
        JobStatusUpdate(
            job_id=JobId.k8s_nextflow("nf-exp-abc"),
            status=JobStatus.FAILED,
            error_message="Job has reached the specified backoff limit",
            error_source="k8s_condition",
        ),
    )
    row = await database_service.get_hpcrun(hpcrun_id)
    assert row is not None
    assert row.error_message == "ValueError: boom"
    assert row.error_source == "command_err"
    assert row.exit_code == 1
    assert row.attempt == 1


@pytest.mark.asyncio
async def test_a_better_source_replaces_a_worse_one_and_an_unlabelled_write_still_wins_over_nothing(
    experiment_request: SimulationRequest, database_service: DatabaseServiceSQL
) -> None:
    hpcrun_id = await _row(database_service, experiment_request)
    await database_service.update_hpcrun_status(
        hpcrun_id,
        JobStatusUpdate(job_id=JobId.k8s_nextflow("nf-exp-abc"), status=JobStatus.FAILED, error_message="backoff"),
    )
    await database_service.update_hpcrun_status(
        hpcrun_id,
        JobStatusUpdate(
            job_id=JobId.k8s_nextflow("nf-exp-abc"),
            status=JobStatus.FAILED,
            error_message="Traceback ...",
            error_source="failure_record",
        ),
    )
    row = await database_service.get_hpcrun(hpcrun_id)
    assert row is not None
    assert row.error_message == "Traceback ..." and row.error_source == "failure_record"


@pytest.mark.asyncio
async def test_a_cancel_without_a_message_clears_stale_error_text(
    experiment_request: SimulationRequest, database_service: DatabaseServiceSQL
) -> None:
    hpcrun_id = await _row(database_service, experiment_request)
    await database_service.update_hpcrun_status(
        hpcrun_id,
        JobStatusUpdate(job_id=JobId.k8s_nextflow("nf-exp-abc"), status=JobStatus.FAILED, error_message="old failure"),
    )
    await database_service.update_hpcrun_status(
        hpcrun_id, JobStatusUpdate(job_id=JobId.k8s_nextflow("nf-exp-abc"), status=JobStatus.CANCELLED)
    )
    row = await database_service.get_hpcrun(hpcrun_id)
    assert row is not None
    assert row.status == JobStatus.CANCELLED and row.error_message is None


@pytest.mark.asyncio
async def test_finalize_nextflow_head_is_single_winner_and_records_partial(
    experiment_request: SimulationRequest, database_service: DatabaseServiceSQL
) -> None:
    import asyncio

    hpcrun_id = await _row(database_service, experiment_request)
    results = await asyncio.gather(
        database_service.finalize_nextflow_head(
            hpcrun_id, JobStatus.PARTIAL, error_message="analysis_v8 failed", error_source="command_err", exit_code=0
        ),
        database_service.finalize_nextflow_head(hpcrun_id, JobStatus.FAILED, error_message="late"),
    )
    assert sorted(results) == [False, True]
    row = await database_service.get_hpcrun(hpcrun_id)
    assert row is not None
    assert row.status in (JobStatus.PARTIAL, JobStatus.FAILED)  # whichever tick won
    assert row.status.is_terminal
    active = await database_service.list_active_nextflow_hpcruns()
    assert all(r.database_id != hpcrun_id for r in active)
