import logging

import pytest

from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.simulation_service import submit_vecoli_job


@pytest.mark.skipif(len(get_settings().slurm_submit_key_path) == 0, reason="slurm ssh key file not supplied")
@pytest.mark.asyncio
async def test_submit_vecoli_job(ssh_service: SSHService, logger: logging.Logger, workspace_image_hash: str) -> None:
    # SIMULATOR_HASH = "079c43c"

    config_id = "sms_perturb_growth"
    experiment_id = "testflow"
    vecoli_repo_hash = workspace_image_hash
    env = get_settings()

    logger.info(
        f"\n>> Running test submission with config id: {config_id}\n>> ...and experiment id: {experiment_id}\n..."
    )
    try:
        jobid = await submit_vecoli_job(
            config_id=config_id,
            simulator_hash=vecoli_repo_hash,
            env=env,
            expid=experiment_id,
            ssh=ssh_service,
            logger=logger,
        )
        logger.info(f"Success! Got slurm jobid: {jobid}")
    except Exception as e:
        logger.info(f">> Not a success!! It was because:\n{e}")
