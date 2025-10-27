import datetime
from textwrap import dedent

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.common.utils import unique_id
from sms_api.config import get_settings
from sms_api.data.models import AnalysisConfig, AnalysisConfigOptions, ExperimentAnalysisRequest
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import get_slurmjob_name
from sms_api.simulation.models import EcoliSimulationDTO, ExperimentMetadata, SimulationConfig


async def insert_mock_simulation(database_service: DatabaseService) -> EcoliSimulationDTO:
    exp_id = "sms_multiseed_0-2794dfa74b9cf37c_1759844363435"
    return await database_service.insert_ecoli_simulation(
        name="sms_multiseed_0",
        config=SimulationConfig(experiment_id=exp_id),
        last_updated=str(datetime.datetime.now()),
        job_name=get_slurmjob_name(experiment_id=exp_id, simulator_hash=get_simulator().git_commit_hash),
        job_id=826660,
        metadata=ExperimentMetadata().model_dump(),
    )


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_run_analysis(
    base_router: str,
    analysis_request: ExperimentAnalysisRequest,
    database_service: DatabaseService,
) -> None:
    # first insert a mock simulation to the db with an existing dataset ref
    _: EcoliSimulationDTO = await insert_mock_simulation(database_service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/analyses", json=analysis_request.model_dump())
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_analysis(
    base_router: str, analysis_request: ExperimentAnalysisRequest, database_service: DatabaseService
) -> None:
    # first insert a mock simulation to the db with an existing dataset ref
    _: EcoliSimulationDTO = await insert_mock_simulation(database_service)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        analyses_url = f"{base_router}/analyses"
        response = await client.post(analyses_url, json=analysis_request.model_dump())
        response.raise_for_status()
        analysis_response = response.json()
        db_id = analysis_response["database_id"]

        fetch_response = await client.get(f"{analyses_url}/{db_id}")
        fetch_response.raise_for_status()
        assert fetch_response.json() == analysis_response


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_outputs(base_router: str, database_service: DatabaseService) -> None:
    exp_name = unique_id(scope="pytest_analysis")
    analysis = await database_service.insert_analysis(
        name="analysis_multigen",
        last_updated=str(datetime.datetime.now()),
        job_name=exp_name,
        job_id=1234,
        config=AnalysisConfig(analysis_options=AnalysisConfigOptions(experiment_id=["sms_multigeneration"])),
    )

    env = get_settings()
    ssh = get_ssh_service(env)
    analysis_data = await database_service.get_analysis(database_id=analysis.database_id)
    output_id = analysis_data.name
    remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
    ret, stdin, stdout = await ssh.run_command(
        dedent(f"""
        cd /home/FCAM/svc_vivarium/workspace \
            && {remote_uv_executable} run scripts/html_outputs.py --output_id {output_id}
    """)
    )
