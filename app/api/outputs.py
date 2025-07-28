import asyncio
import logging
import os
import re
from pathlib import Path

import asyncssh
from asyncssh import SSHCompletedProcess

from sms_api.common.gateway.models import Namespace
from sms_api.config import get_settings

logger = logging.getLogger(__file__)
settings = get_settings()

results_dir_root = Path(__file__).parent.parent.parent / "results"
experiment_id = "experiment_78c6310_id_149_20250723-112814"


async def run_ssh_command(conn, command):
    try:
        logger.info(f"Running ssh command: {command}")
        result: SSHCompletedProcess = await conn.run(command, check=True)
        if not isinstance(result.stdout, str):
            raise TypeError(f"Expected result.stdout to be str, got {type(result.stdout)}")
        if not isinstance(result.stderr, str):
            raise TypeError(f"Expected result.stderr to be str, got {type(result.stderr)}")
        if not isinstance(result.returncode, int):
            raise TypeError(f"Expected result.returncode to be int, got {type(result.returncode)}")
        logger.info(
            msg=f"command {command} retcode {result.returncode} "
            f"stdout={result.stdout[:100]} stderr={result.stderr[:100]}"
        )
        return result.returncode, result.stdout, result.stderr
    except asyncssh.ProcessError as exc:
        logger.exception(msg=f"failed to send command {command}, stderr {str(exc.stderr)[:100]}", exc_info=exc)
        raise RuntimeError(f"failed to send command {command}, stderr {str(exc.stderr)[:100]})") from exc
    except (OSError, asyncssh.Error) as exc:
        logger.exception(msg=f"failed to send command {command}, stderr {str(exc)[:100]}", exc_info=exc)
        raise RuntimeError(f"failed to send command {command}, error {str(exc)[:100]}") from exc


async def get_simulation_chunk_paths(conn, experiment_id: str, namespace: Namespace) -> list[Path]:
    experiment_dir = Path(f"{settings.slurm_base_path}/{namespace}/sims/{experiment_id}")
    chunks_dir = Path(
        os.path.join(
            experiment_dir,
            "history",
            f"experiment_id={experiment_id}",
            "variant=0",
            "lineage_seed=0",
            "generation=1",
            "agent_id=0",
        )
    )
    ret, stdout, stderr = await run_ssh_command(conn, f"ls -al {chunks_dir} | grep .pq")
    filenames = [Path(os.path.join(chunks_dir, fname)) for fname in re.findall(r"(\d+\.pq)", stdout)]
    return filenames


def get_chunks_dirpath(experiment_id: str) -> Path:
    """Get the remote (uchc hpc) dirpath of a given simulation's chunked parquet outputs"""
    return Path(
        f"/home/FCAM/svc_vivarium/prod/sims/{experiment_id}/history/experiment_id={experiment_id}/variant=0/lineage_seed=0/generation=1/agent_id=0"
    )


async def download_chunks(experiment_id: str, namespace: Namespace | None = None):
    # get dirs for appropriate namespace
    sim_namespace = namespace or Namespace.PRODUCTION
    remote_dirpath = get_chunks_dirpath(experiment_id)
    local_dirpath = results_dir_root / experiment_id
    if not os.path.exists(local_dirpath):
        os.mkdir(local_dirpath)

    # setup ssh
    hostname = settings.slurm_submit_host
    username = settings.slurm_submit_user
    keypath = Path(settings.slurm_submit_key_path)
    known_hosts = Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None

    async with asyncssh.connect(
        host=hostname, username=username, client_keys=[keypath], known_hosts=known_hosts
    ) as conn:
        try:
            # first get available chunks
            available_chunks: list[Path] = await get_simulation_chunk_paths(
                conn=conn, experiment_id=experiment_id, namespace=sim_namespace
            )

            # then iteratively download chunks
            for remote_path in available_chunks:
                local_path = local_dirpath / remote_path.name
                await asyncssh.scp(srcpaths=(conn, remote_path), dstpath=local_path)
                logger.info(f"Downloaded chunk: {remote_path.name}")
        except asyncssh.Error as exc:
            logger.exception(msg=f"failed to retrieve remote file {remote_path} to {local_file}", exc_info=exc)
            raise RuntimeError(
                f"failed to retrieve remote file {remote_path} to {local_file}, error {str(exc)[:100]}"
            ) from exc


async def download_chunks_batch(experiment_id: str, namespace: Namespace | None = None):
    # set up namespace and appropriate experiment dir
    sim_namespace = namespace or Namespace.PRODUCTION
    remote_dirpath = get_chunks_dirpath(experiment_id)
    local_dirpath = results_dir_root / experiment_id
    if not os.path.exists(local_dirpath):
        os.mkdir(local_dirpath)

    # set up ssh TODO: modify service for persistent conn
    hostname = settings.slurm_submit_host
    username = settings.slurm_submit_user
    keypath = Path(settings.slurm_submit_key_path)
    known_hosts = Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None

    semaphore = asyncio.Semaphore(10)

    async with asyncssh.connect(
        host=hostname, username=username, client_keys=[keypath], known_hosts=known_hosts
    ) as conn:
        try:
            # Get available chunks
            available_chunks: list[Path] = await get_simulation_chunk_paths(
                conn=conn, experiment_id=experiment_id, namespace=sim_namespace
            )

            # Create download tasks with semaphore limit
            async def download(remote_path: Path):
                async with semaphore:
                    local_path = local_dirpath / remote_path.name
                    await asyncssh.scp(srcpaths=(conn, remote_path), dstpath=local_path)
                    logger.info(f"Downloaded chunk: {remote_path.name}")
                    return remote_path.name

            # Run downloads in parallel with limit
            await asyncio.gather(*(download(remote_path) for remote_path in available_chunks))

        except asyncssh.Error as exc:
            logger.exception(msg=f"failed to retrieve remote file {remote_path} to {local_path}", exc_info=exc)
            raise RuntimeError(
                f"failed to retrieve remote file {remote_path} to {local_path}, error {str(exc)[:100]}"
            ) from exc
