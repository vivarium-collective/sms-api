import datetime
import json
from textwrap import dedent
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.api.request_examples import analysis_ptools, generate_analysis_request
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.common.utils import unique_id
from sms_api.config import REPO_ROOT, get_settings
from sms_api.data.models import AnalysisConfig, AnalysisConfigOptions, AnalysisDomain, ExperimentAnalysisRequest
from sms_api.data.sim_analysis_service import AnalysisService
from sms_api.dependencies import get_database_service, init_standalone
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
        assert len(data) == 3


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

    ssh = get_ssh_service()
    analysis_data = await database_service.get_analysis(database_id=analysis.database_id)
    output_id = analysis_data.name
    remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
    ret, stdin, stdout = await ssh.run_command(
        dedent(f"""
        cd /home/FCAM/svc_vivarium/workspace \
            && {remote_uv_executable} run scripts/html_outputs.py --output_id {output_id}
    """)
    )


def normalize_config(config: dict[str, Any]) -> str:
    """
    Convert config dict to a canonical JSON string
    for stable equality comparison.
    """
    # Sort multiseed list by `name` to avoid order issues
    sorted_multiseed = sorted(config["multiseed"], key=lambda x: (x["name"], x["variant"], x["n_tp"]))

    normalized = {"experiment_id": config["experiment_id"], "multiseed": sorted_multiseed}

    # Return canonical JSON representation
    return json.dumps(normalized, sort_keys=True)


def check_duplicate(request_config: dict[str, Any], saved_configs: list[dict[str, Any]]) -> bool:
    """
    Returns True if request_config matches any saved config.
    """
    req_norm = normalize_config(request_config)

    for cfg in saved_configs:
        if normalize_config(cfg) == req_norm:
            return True

    return False


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_check_duplicate(
    # database_service: DatabaseServiceSQL
) -> None:
    await init_standalone()
    database_service = get_database_service()
    new_analysis_request: dict = analysis_ptools.model_dump()
    saved_analysis_configs: list = [config.model_dump() for config in (await database_service.list_analyses())]

    needs_processing = True
    if check_duplicate(new_analysis_request, saved_analysis_configs):
        needs_processing = False

    print(f"Job needs processing: {needs_processing}\nRequested Payload:\n{new_analysis_request}")


@pytest.mark.asyncio
async def test_generate_analysis_request() -> None:
    requested_configs = AnalysisDomain.to_list()
    request = generate_analysis_request(requested_configs)
    analysis_name = AnalysisService.generate_analysis_name()
    config = request.to_config(analysis_name, get_settings())
    with open(f"{REPO_ROOT}/assets/{analysis_name}.json", "w") as fp:
        json.dump(config.model_dump(), fp, indent=4)

    print()
