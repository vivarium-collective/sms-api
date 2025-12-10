import os
from typing import Any

import pytest

from sms_api.api.routers.ecoli import connect_ssh
from sms_api.common.ssh.ssh_service import get_ssh_service_managed
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import get_settings
from sms_api.data.handlers import (
    CACHE_DIR,
    DEFAULT_ANALYSIS,
    DEFAULT_EXPERIMENT,
    PartitionRequest,
    get_ptools_analysis_request,
    get_ptools_analysis_request_config,
    get_ptools_output,
)
from sms_api.data.models import (
    AnalysisConfig,
    ExperimentAnalysisRequest,
    PtoolsAnalysisConfig,
    TsvOutputFile,
)


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
    async def func(x: float, y: float, **kwargs: Any) -> float:
        return x + y

    ssh = get_ssh_service_managed()
    z = await func(11.11, 2.2, ssh_service=ssh)
    print(z)
    assert not ssh.connected
