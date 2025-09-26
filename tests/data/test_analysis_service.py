import logging

import pytest

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.data.services.analysis import OutputFile, get_tsv_outputs_local


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_get_tsv_outputs_local(ssh_service: SSHService, logger: logging.Logger) -> None:
    output_id = "ptools_multigen_analysis_alex"
    outputs = await get_tsv_outputs_local(ssh_service=ssh_service, output_id=output_id)
    assert all(isinstance(output, OutputFile) for output in outputs)
