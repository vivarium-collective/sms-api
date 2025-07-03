import asyncio
from functools import lru_cache
import glob
import json
import logging
import os
import random
import re
import shutil
import string
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent
from threading import local
import time
from typing import Any, Callable, Iterator

from anyio import mkdtemp
from async_lru import alru_cache
from asyncssh import SSHClientConnection
import dask
import dask.dataframe as ddf
from dask.distributed import Client
import polars as pl
from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.sim_utils import get_single_simulation_chunks_dirpath, read_latest_commit
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import Settings, get_settings
from sms_api.simulation.database_service import SimulationDatabaseService
from sms_api.simulation.hpc_utils import (
    get_remote_chunks_dirpath,
)
from sms_api.simulation.models import EcoliSimulation, Namespaces, ParcaDataset, SimulatorVersion

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEST_CHUNK_DIR = Path("assets/tests/test_history")
TEST_CHUNK_PATH = TEST_CHUNK_DIR / "1200.pq"
TEST_EXPERIMENT_ID = "experiment_96bb7a2_id_1_20250620-181422"


class DataService(ABC):
    settings: Settings

    def __init__(
            self, 
            settings: Settings | None = None
        ) -> None:
        self.settings = settings or get_settings()

    @property
    def ssh_service(self) -> SSHService:
        return get_ssh_service(settings=self.settings)
    

class DataServiceHpc(DataService):
    def get_remote_chunk_path(self, db_id: int, commit_hash: str, chunk_id: int, namespace: Namespaces | None = None) -> Path:
        results_fname = f"{chunk_id}.pq"

        # get remote dirpath
        remote_dirpath = get_remote_chunks_dirpath(db_id, commit_hash, namespace or Namespaces.TEST)
        return remote_dirpath / results_fname
    
    async def download_chunk(self, remote_chunk_path: Path, local_dirpath: Path | None = None) -> Path:
        # make local mirror for temp
        results_fname = str(remote_chunk_path).split('/')[-1]
        local_dest = local_dirpath or Path(tempfile.mkdtemp())
        local_fpath = local_dest  / results_fname

        try:
            await self.ssh_service.scp_download(local_file=local_fpath, remote_path=remote_chunk_path)
            return local_fpath
        except Exception as e:
            raise e
        
    async def get_simulation_chunk_paths(self, experiment_id: str, namespace: Namespaces) -> list[Path]:
        experiment_dir = Path(f"{self.settings.slurm_base_path}/{namespace}/sims/{experiment_id}")
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
        ret, stdout, stderr = await self.ssh_service.run_command(f"ls -al {chunks_dir} | grep .pq")
        filenames = [Path(os.path.join(chunks_dir, fname)) for fname in re.findall(r'(\d+\.pq)', stdout)]
        return filenames
    
    @alru_cache
    async def read_simulation_chunks(self, experiment_id: str, namespace: Namespaces) -> tuple[Path, pl.LazyFrame]:
        # TODO: instead use a session so as to not iteratively reauth
        local_chunks_dir = Path(await mkdtemp(dir="datamount", prefix=experiment_id))
        for chunkpath in await self.get_simulation_chunk_paths(experiment_id, namespace):
            local_fp = local_chunks_dir / chunkpath.parts[-1]
            await self.ssh_service.scp_download(local_file=local_fp, remote_path=chunkpath)
            
        return local_chunks_dir, self.scan_simulation_chunks(local_chunks_dir)
    
    def scan_simulation_chunks(self, chunks_dirpath: Path):
        return pl.scan_parquet(f"{str(chunks_dirpath)}/*.pq", rechunk=True)

