import pytest

from sms_api.common.handlers.simulations import fetch_omics_outputs, get_available_omics_output_paths
from sms_api.common.ssh.ssh_service import SSHSessionService
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import get_settings


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_available_omics_output_paths(
    ssh_session_service: SSHSessionService, analysis_outdir: HPCFilePath
) -> None:
    results = await get_available_omics_output_paths(remote_analysis_outdir=analysis_outdir)
    assert len(results), "No files found."
    assert all([isinstance(fp, HPCFilePath) and fp.remote_path.__str__().endswith(".txt") for fp in results])


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_fetch_simulation_omics_outputs(
    ssh_session_service: SSHSessionService, analysis_outdir: HPCFilePath
) -> None:
    results = await fetch_omics_outputs(exp_analysis_outdir=analysis_outdir)
    assert len(results)
