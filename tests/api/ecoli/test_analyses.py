import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.gateway.utils import generate_analysis_request
from sms_api.common.utils import get_uuid, unique_id
from sms_api.config import get_settings
from sms_api.data.models import AnalysisConfig, AnalysisConfigOptions, AnalysisDomain, ExperimentAnalysisRequest
from sms_api.simulation.database_service import DatabaseService


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_run_analysis(
    base_router: str,
    analysis_request: ExperimentAnalysisRequest,
    database_service: DatabaseService,
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/analyses", json=analysis_request.model_dump())
        response.raise_for_status()
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 6


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
        name="analysis_multigen",
        last_updated=str(datetime.datetime.now()),
        job_name=exp_name,
        job_id=1234,
        config=AnalysisConfig(analysis_options=AnalysisConfigOptions(experiment_id=["sms_multigeneration"])),
    )
    analysis_data = await database_service.get_analysis(database_id=analysis.database_id)
    assert analysis_data.name == "analysis_multigen"


@pytest.mark.skipif(len(str(get_settings().simulation_outdir)) == 0, reason="simulation outdir not supplied")
@pytest.mark.asyncio
async def test_generate_analysis_request() -> None:
    experiment_id = "test_experiment"
    request = generate_analysis_request(
        experiment_id="test_experiment", analysis_name="analysis_test", requested_configs=AnalysisDomain.to_list()
    )

    analysis_name = request.analysis_name or get_uuid(scope="analysis")
    config = request.to_config(analysis_name, get_settings())

    env = get_settings()
    expected_variant_dir = str(env.simulation_outdir / experiment_id / "variant_sim_data")

    actual_options = config.analysis_options
    assert actual_options.variant_data_dir == [expected_variant_dir]
    assert actual_options.experiment_id == [experiment_id]
