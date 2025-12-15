import json
import logging
import os
from typing import Any

import pytest
from pydantic import BaseModel

from sms_api.api import request_examples
from sms_api.api.request_examples import analysis_ptools
from sms_api.common.gateway.utils import connect_ssh, generate_analysis_request, get_simulator
from sms_api.common.ssh.ssh_service import SSHServiceManaged, get_ssh_service_managed
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import REPO_ROOT, get_settings
from sms_api.data import analysis_service as sas
from sms_api.data._handlers import (
    CACHE_DIR,
    DEFAULT_ANALYSIS,
    DEFAULT_EXPERIMENT,
    PartitionRequest,
    get_ptools_analysis_request,
    get_ptools_analysis_request_config,
    get_ptools_output,
)
from sms_api.data.analysis_service import AnalysisServiceHpc
from sms_api.data.models import (
    AnalysisConfig,
    AnalysisDomain,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    TsvOutputFile,
)

GENERATE_ARTIFACTS = True


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_from_partition_request_dirpath() -> None:
    config = PtoolsAnalysisConfig()
    partition: PartitionRequest = PartitionRequest.from_ptools_analysis_request(
        experiment_id="sms_multiseed_0-2794dfa74b9cf37c_1759844363435",
        config=config,
        analysis_name="sms_analysis-ad95c6471274a2d1_1762384004486",
    )
    env = get_settings()
    outdir = partition.to_dirpath(env.simulation_outdir)
    ssh = get_ssh_service_managed()
    await ssh.connect()
    try:
        output_dir = outdir.remote_path if isinstance(outdir, HPCFilePath) else outdir
        ret, stdout, stderr = await ssh.run_command(f"ls {output_dir!s}")
        assert stdout == "ptools_rna_multiseed.txt\n"
        print(stdout)
    finally:
        await ssh.disconnect()
        print("SSH Disconnected")


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_analysis_request(
    ptools_analysis_request: ExperimentAnalysisRequest, analysis_request_config: AnalysisConfig
) -> None:
    ptools_modname: str = list(analysis_request_config.analysis_options.multiseed.keys())[0]  # noqa: RUF015
    config = PtoolsAnalysisConfig(name=ptools_modname, n_tp=8)
    output_dir = analysis_request_config.analysis_options.outdir
    assert output_dir is not None
    analysis_name = output_dir.split("/")[-1]
    partition: PartitionRequest = PartitionRequest.from_ptools_analysis_request(
        experiment_id=ptools_analysis_request.experiment_id, config=config, analysis_name=analysis_name
    )
    filename = "ptools_rna_multiseed.txt"
    env = get_settings()
    outdir = partition.to_dirpath(env.simulation_outdir)
    ssh = get_ssh_service_managed()
    await ssh.connect()
    assert ssh.connected
    try:
        fp = outdir.remote_path if isinstance(outdir, HPCFilePath) else outdir / filename
        remote = HPCFilePath(remote_path=fp)
        local_dir = CACHE_DIR / analysis_name
        if not local_dir.exists():
            os.mkdir(str(local_dir))
        local = local_dir / filename

        # save to cache if not exists
        if not local.exists():
            await ssh.scp_download(local_file=local, remote_path=remote)

        content = local.read_text()
        print(content)
    finally:
        await ssh.disconnect()
        assert not ssh.connected


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_ptools_output() -> None:
    expid = DEFAULT_EXPERIMENT
    analysis_name = DEFAULT_ANALYSIS
    fname = "ptools_rna_multiseed.txt"
    request = get_ptools_analysis_request(expid)
    config = get_ptools_analysis_request_config(request, analysis_name)
    ssh = get_ssh_service_managed()
    await ssh.connect()
    try:
        assert ssh.connected, "SSH is not connected"
        tsv_output: TsvOutputFile = await get_ptools_output(ssh, request, config, fname)
        assert tsv_output.filename == fname
        assert tsv_output.variant == 0
        assert tsv_output.content is not None
        assert tsv_output.content.startswith("$\tt0\tt1\tt2\tt3\tt4\tt5\tt6\tt7")
    finally:
        await ssh.disconnect()
        print(f"SSH CONNECTED: {ssh.connected}")


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_connect_ssh() -> None:
    @connect_ssh
    async def generate(x: float, y: float, **kwargs: Any) -> float:
        z = x + y
        ssh_svc: SSHServiceManaged = kwargs["ssh_service"]
        cmd = f'echo "{z}" > /home/FCAM/svc_vivarium/workspace/test_connect_ssh.txt'
        await ssh_svc.run_command(cmd)
        return z

    @connect_ssh
    async def check(**kwargs):
        ssh_svc: SSHServiceManaged = kwargs.get("ssh_service")
        test_path = "/home/FCAM/svc_vivarium/workspace/test_connect_ssh.txt"
        ret, stdout, stderr = await ssh_svc.run_command(f"cat {test_path}")
        print(stdout)

    ssh = get_ssh_service_managed()
    z = await generate(11.11, 2.2, ssh_service=ssh)
    await check(ssh_service=ssh)
    print(z)
    assert not ssh.connected


@pytest.mark.asyncio
async def test_collect_parameters() -> None:
    svc = sas.AnalysisServiceHpc()
    request = analysis_ptools
    simulator_hash = get_simulator().git_commit_hash

    (experiment_id, analysis_name, analysis_config, slurmjob_name, slurm_log_file) = svc._collect_parameters(
        request=request, simulator_hash=simulator_hash
    )
    print()


@pytest.mark.asyncio
async def test_generate_slurm_script(
    analysis_service: AnalysisServiceHpc, ptools_analysis_config: AnalysisConfig
) -> None:
    request = request_examples.analysis_ptools2
    simulator_hash = get_simulator().git_commit_hash

    (experiment_id, analysis_name, analysis_config, slurmjob_name, slurm_log_file) = (
        analysis_service._collect_parameters(request=request, simulator_hash=simulator_hash)
    )
    slurm_script = analysis_service.generate_slurm_script(
        slurm_log_file=slurm_log_file,
        slurm_job_name=slurmjob_name,
        latest_hash=simulator_hash,
        config=analysis_config,
        analysis_name=analysis_name,
    )

    with open(f"assets/{analysis_name}.sbatch", "w") as fp:
        fp.write(slurm_script)


@pytest.mark.asyncio
async def test_parse_request(analysis_service: AnalysisServiceHpc) -> None:
    request = analysis_ptools

    env = get_settings()
    name = analysis_service.generate_analysis_name(experiment_id=request.experiment_id)

    exported: AnalysisConfig = request.to_config(analysis_name=name, env=env)
    imported: AnalysisConfig = AnalysisConfig.from_request(request=request, analysis_name=name)

    def serialize(dto: BaseModel) -> dict:
        return dto.model_dump()

    assert serialize(exported) == serialize(imported)

    print()


@pytest.mark.asyncio
async def test_analysis_roundtrip(analysis_service: AnalysisServiceHpc, logger: logging.Logger) -> None:
    # generate/write config JSON
    exp_id = "publication_multiseed_multigen-a7ae0b4e093e20e6_1762830572273"
    requested_configs = AnalysisDomain.to_list()
    request: ExperimentAnalysisRequest = generate_analysis_request(
        experiment_id=exp_id, requested_configs=requested_configs
    )

    # the rest should effectively recreate the logic performed in analysis_handlers.run_analysis()
    # parameterize the generation of slurm script with config/request
    simulator_hash = get_simulator().git_commit_hash
    (experiment_id, analysis_name, analysis_config, slurmjob_name, slurm_log_file) = (
        analysis_service._collect_parameters(request=request, simulator_hash=simulator_hash)
    )

    # generate and dispatch script
    slurm_script = analysis_service.generate_slurm_script(
        slurm_log_file=slurm_log_file,
        slurm_job_name=slurmjob_name,
        latest_hash=simulator_hash,
        config=analysis_config,
        analysis_name=analysis_name,
    )

    if GENERATE_ARTIFACTS:
        # write vEcoli config JSON
        with open(f"{REPO_ROOT}/assets/artifacts/{analysis_name}.json", "w") as fp:
            json.dump(analysis_config.model_dump(), fp, indent=4)
        # write corresponding sbatch
        with open(f"{REPO_ROOT}/assets/artifacts/{analysis_name}.sbatch", "w") as fp:
            fp.write(slurm_script)

    # dispatch analysis SLURM job
    slurmjob_name, slurmjob_id = await analysis_service.dispatch_analysis(
        request=request, logger=logger, simulator_hash=simulator_hash, analysis_name=analysis_name
    )

    # poll status

    # scp download to .results_cache / store to vecdb

    # return loaded outputs as dtos
