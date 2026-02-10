import logging

import pytest
import pytest_asyncio

from sms_api.analysis.analysis_service import AnalysisServiceSlurm
from sms_api.analysis.models import ExperimentAnalysisRequest, PtoolsAnalysisConfig
from sms_api.common.handlers.analyses import handle_run_analysis_slurm
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import SimulatorVersion
from sms_api.simulation.simulation_service import SimulationServiceHpc


@pytest_asyncio.fixture
async def analysis_request() -> ExperimentAnalysisRequest:
    return ExperimentAnalysisRequest(
        experiment_id="sim1-1seed_1generation-cc24",
        multiseed=[PtoolsAnalysisConfig(name="ptools_rna", n_tp=8, variant=0)],
    )


@pytest_asyncio.fixture
async def simulator_version() -> SimulatorVersion:
    return SimulatorVersion(**{
        "git_commit_hash": "203ab2a",
        "git_repo_url": "https://github.com/vivarium-collective/vEcoli",
        "git_branch": "api-support",
        "database_id": 1,
        "created_at": "2026-02-04T21:08:38.272533",
    })


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_handle_run_analysis_slurm(
    analysis_request: ExperimentAnalysisRequest,
    database_service: DatabaseService,
    ssh_session_service: SSHSessionService,
    simulation_service_slurm: SimulationServiceHpc,
    simulator_version: SimulatorVersion,
    logger: logging.Logger,
) -> None:
    result = await handle_run_analysis_slurm(
        request=analysis_request,
        analysis_service=AnalysisServiceSlurm(env=get_settings()),
        simulator=simulator_version,
        logger=logger,
        db_service=database_service,
    )
