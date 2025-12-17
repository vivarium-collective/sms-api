import pytest

from sms_api.analysis.analysis_service import AnalysisService, connect_ssh
from sms_api.analysis.analysis_service_slurm import AnalysisServiceSlurm
from sms_api.analysis.models import (
    AnalysisConfig,
)
from sms_api.api import request_examples
from sms_api.api.request_examples import analysis_ptools
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.ssh.ssh_service import SSHServiceManaged
from sms_api.config import get_settings

ENV = get_settings()
GENERATE_ARTIFACTS = True


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_connect_ssh() -> None:
    testpath = "/home/FCAM/svc_vivarium/workspace/test_connect_ssh.txt"

    @connect_ssh
    async def generate(self: AnalysisService, x: float, y: float) -> float:
        z = x + y
        ssh_svc: SSHServiceManaged = self.ssh

        cmd = f'echo "{z}" > {testpath} && cat {testpath}'
        await ssh_svc.run_command(cmd)
        return z

    @connect_ssh
    async def cleanup(self: AnalysisService) -> None:
        ssh_svc: SSHServiceManaged = self.ssh
        ret, stdout, stderr = await ssh_svc.run_command(f"rm -f {testpath}")
        return None

    analysis_service = AnalysisServiceSlurm(ENV)
    z = await generate(analysis_service, 11.11, 2.2)
    await cleanup(analysis_service)
    print(z)
    assert not analysis_service.ssh.connected


@pytest.mark.asyncio
async def test_generate_slurm_script(
    analysis_service: AnalysisServiceSlurm, ptools_analysis_config: AnalysisConfig
) -> None:
    request = request_examples.analysis_ptools
    simulator_hash = get_simulator().git_commit_hash
    name = "test_generate_slurm_script"
    analysis_config = request.to_config(analysis_name=name)

    slurmjob_name, slurm_log_file = analysis_service._collect_slurm_parameters(
        request=request, simulator_hash=simulator_hash, analysis_name=name
    )

    slurm_script = analysis_service.generate_slurm_script(
        slurm_log_file=slurm_log_file,
        slurm_job_name=slurmjob_name,
        latest_hash=simulator_hash,
        config=analysis_config,
        analysis_name=name,
    )

    assert isinstance(slurm_script, str)


@pytest.mark.asyncio
async def test_parse_request(analysis_service: AnalysisServiceSlurm) -> None:
    request = analysis_ptools

    env = get_settings()
    name = analysis_service.generate_analysis_name(experiment_id=request.experiment_id)

    exported: AnalysisConfig = request.to_config(analysis_name=name, env=env)
    imported: AnalysisConfig = AnalysisConfig.from_request(request=request, analysis_name=name)

    assert exported.model_dump() == imported.model_dump()

    print()
