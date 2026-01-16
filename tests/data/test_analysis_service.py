import pytest

from sms_api.analysis.analysis_service import AnalysisServiceSlurm, RequestPayload
from sms_api.analysis.models import (
    AnalysisConfig,
)
from sms_api.api import request_examples
from sms_api.config import get_settings

ENV = get_settings()
GENERATE_ARTIFACTS = True

# Test simulator hash - used for unit tests only
TEST_SIMULATOR_HASH = "test123abc"


@pytest.mark.asyncio
async def test_generate_slurm_script(
    analysis_service: AnalysisServiceSlurm,
    analysis_request_config: AnalysisConfig,
) -> None:
    request = request_examples.analysis_ptools
    simulator_hash = TEST_SIMULATOR_HASH
    name = "test_generate_slurm_script"
    analysis_config = request.to_config(analysis_name=name, env=ENV)

    slurmjob_name, slurm_log_file = analysis_service._collect_slurm_parameters(
        request=request, simulator_hash=simulator_hash, analysis_name=name
    )

    slurm_script = analysis_service._generate_slurm_script(
        slurm_log_file=slurm_log_file,
        slurm_job_name=slurmjob_name,
        latest_hash=simulator_hash,
        config=analysis_config,
        analysis_name=name,
    )

    assert isinstance(slurm_script, str)


@pytest.mark.asyncio
async def test_normalize() -> None:
    from sms_api.api.request_examples import analysis_request_base

    origin = analysis_request_base.model_dump()
    payload1 = RequestPayload(data=origin)
    h1 = payload1.hash()
    assert h1 == RequestPayload(data=origin).hash()
