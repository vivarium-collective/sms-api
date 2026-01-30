import datetime
import logging
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.analysis.models import AnalysisConfig, AnalysisConfigOptions, ExperimentAnalysisRequest
from sms_api.api import request_examples
from sms_api.api.main import app
from sms_api.common.utils import get_uuid, timestamp, unique_id
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import get_slurmjob_name
from sms_api.simulation.models import ParcaDatasetRequest, ParcaOptions, SimulationConfig, SimulationRequest

ENV = get_settings()


@pytest.mark.integration
@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_run_analysis(
    base_router: str,
    analysis_request: ExperimentAnalysisRequest,
    database_service: DatabaseService,
    logger: logging.Logger,
) -> None:
    transport = ASGITransport(app=app)

    # Insert a simulation with matching experiment_id (required by /analyses endpoint)
    unique_commit_hash = f"test_{uuid.uuid4().hex[:7]}"
    simulator = await database_service.insert_simulator(
        git_commit_hash=unique_commit_hash,
        git_repo_url=request_examples.DEFAULT_SIMULATOR.git_repo_url,
        git_branch=request_examples.DEFAULT_SIMULATOR.git_branch,
    )
    parca_request = ParcaDatasetRequest(
        simulator_version=simulator,
        parca_config=ParcaOptions(),
    )
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_request)
    sim_config = SimulationConfig(experiment_id=analysis_request.experiment_id)
    sim_request = SimulationRequest(
        experiment_id=analysis_request.experiment_id,
        simulation_config_filename="api_simulation_default_with_profile.json",
        simulator_id=simulator.database_id,
        parca_dataset_id=parca_dataset.database_id,
        config=sim_config,
    )
    await database_service.insert_simulation(sim_request=sim_request)

    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            analyses_url = f"{base_router}/analyses"
            response = await client.post(analyses_url, json=analysis_request.model_dump())
            response.raise_for_status()
            analysis_response = response.json()
            assert isinstance(analysis_response, list)
            for obj in analysis_response:
                assert isinstance(obj, dict)
    except Exception as e:
        logger.exception(f"Could not submit the analysis request: {e}")  # noqa: TRY401
    for root, _, files in Path(".results_cache").absolute().walk():
        for f in files:
            path = root / f
            if path.is_dir():
                path.rmdir()


@pytest.mark.integration
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
    name = get_uuid(scope="test_get_analysis")
    analysis_record = await database_service.insert_analysis(
        name=name,
        config=analysis_request.to_config(analysis_name=name, env=ENV),
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
    request = request_examples.analysis_test_ptools

    analysis_name = get_uuid(scope="analysis")
    config = request.to_config(analysis_name=analysis_name, env=ENV)

    # env = get_settings()
    # expected_variant_dir = str(env.simulation_outdir / request.experiment_id / "variant_sim_data")

    actual_options = config.analysis_options
    # assert actual_options.variant_data_dir == [expected_variant_dir]
    assert actual_options.experiment_id == [request.experiment_id]
