import datetime
from textwrap import dedent

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.common.utils import unique_id
from sms_api.config import get_settings
from sms_api.data.models import AnalysisConfig, AnalysisConfigOptions, ExperimentAnalysisRequest
from sms_api.simulation.database_service import DatabaseService


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_run_analysis(
    base_router: str, analysis_request: ExperimentAnalysisRequest, database_service: DatabaseService
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/analyses", json=analysis_request.model_dump())
        response.raise_for_status()
        data = response.json()
        assert isinstance(data["config"]["analysis_options"]["experiment_id"], list)


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_analysis(
    base_router: str, analysis_request: ExperimentAnalysisRequest, database_service: DatabaseService
) -> None:
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


@pytest.mark.asyncio
async def test_get_outputs(base_router: str, database_service: DatabaseService) -> None:
    exp_name = unique_id(scope="pytest_analysis")
    analysis = await database_service.insert_analysis(
        name=exp_name,
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
