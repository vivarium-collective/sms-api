import datetime
import logging

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.common.gateway.utils import generate_analysis_request
from sms_api.common.utils import get_uuid, timestamp, unique_id
from sms_api.config import get_settings
from sms_api.data.models import AnalysisConfig, AnalysisConfigOptions, AnalysisDomain, ExperimentAnalysisRequest
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import get_slurmjob_name

ENV = get_settings()


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_run_analysis(
    base_router: str,
    analysis_request: ExperimentAnalysisRequest,
    database_service: DatabaseService,
) -> None:
    transport = ASGITransport(app=app)
    data = None
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/analyses", json=analysis_request.model_dump())
        response.raise_for_status()
        data = response.json()

    assert data is not None
    assert isinstance(data, list)
    assert len(data) == 6


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_analysis(
    base_router: str,
    analysis_request: ExperimentAnalysisRequest,
    database_service: DatabaseService,
    logger: logging.Logger,
) -> None:
    transport = ASGITransport(app=app)
    slurmjob_name = get_slurmjob_name(experiment_id=analysis_request.experiment_id)
    analysis_request.analysis_name = get_uuid(scope="test_get_analysis")
    analysis_record = await database_service.insert_analysis(
        name=get_uuid(scope="test_get_analysis"),
        config=analysis_request.to_config(env=ENV),
        last_updated=timestamp(),
        job_name=slurmjob_name,
        job_id=111122,
    )
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        analyses_url = f"{base_router}/analyses/{analysis_record.database_id}"
        response = await client.get(analyses_url)
        response.raise_for_status()
        analysis_response = response.json()
        experiment_ids = analysis_response["config"]["analysis_options"]["experiment_id"]
        assert isinstance(experiment_ids, list)
        assert experiment_ids == [analysis_request.experiment_id]


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
    config = request.to_config(analysis_name=analysis_name, env=ENV)

    env = get_settings()
    expected_variant_dir = str(env.simulation_outdir / experiment_id / "variant_sim_data")

    actual_options = config.analysis_options
    assert actual_options.variant_data_dir == [expected_variant_dir]
    assert actual_options.experiment_id == [experiment_id]
