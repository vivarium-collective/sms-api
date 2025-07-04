import logging
import os
import re
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

import polars as pl
from anyio import mkdtemp
from async_lru import alru_cache
from typing_extensions import override

from sms_api.common.gateway.models import Namespace
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import Settings, get_settings
from sms_api.simulation.hpc_utils import (
    get_remote_chunks_dirpath,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEST_CHUNK_DIR = Path("assets/tests/test_history")
TEST_CHUNK_PATH = TEST_CHUNK_DIR / "1200.pq"
TEST_EXPERIMENT_ID = "experiment_96bb7a2_id_1_20250620-181422"


class DataService(ABC):
    settings: Settings

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def ssh_service(self) -> SSHService:
        return get_ssh_service(settings=self.settings)

    @abstractmethod
    def get_remote_chunk_path(
        self, db_id: int, commit_hash: str, chunk_id: int, namespace: Namespace | None = None
    ) -> Path:
        pass

    @abstractmethod
    async def download_chunk(self, remote_chunk_path: Path, local_dirpath: Path | None = None) -> Path:
        pass

    @abstractmethod
    async def get_simulation_chunk_paths(self, experiment_id: str, namespace: Namespace) -> list[Path]:
        pass

    @abstractmethod
    async def read_simulation_chunks(self, experiment_id: str, namespace: Namespace) -> tuple[Path, pl.LazyFrame]:
        pass

    def scan_simulation_chunks(self, chunks_dirpath: Path) -> pl.LazyFrame:
        return pl.scan_parquet(f"{chunks_dirpath!s}/*.pq", rechunk=True)

    @abstractmethod
    async def close(self) -> None:
        pass


class DataServiceHpc(DataService):
    @override
    def get_remote_chunk_path(
        self, db_id: int, commit_hash: str, chunk_id: int, namespace: Namespace | None = None
    ) -> Path:
        results_fname = f"{chunk_id}.pq"

        # get remote dirpath
        remote_dirpath = get_remote_chunks_dirpath(db_id, commit_hash, namespace or Namespace.TEST)
        return remote_dirpath / results_fname

    async def download_chunk(self, remote_chunk_path: Path, local_dirpath: Path | None = None) -> Path:
        # make local mirror for temp
        results_fname = str(remote_chunk_path).split("/")[-1]
        local_dest = local_dirpath or Path(tempfile.mkdtemp())
        local_fpath = local_dest / results_fname

        try:
            await self.ssh_service.scp_download(local_file=local_fpath, remote_path=remote_chunk_path)
            return local_fpath
        except Exception as e:
            raise OSError(e) from e

    @alru_cache
    async def get_simulation_chunk_paths(self, experiment_id: str, namespace: Namespace) -> list[Path]:
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
        filenames = [Path(os.path.join(chunks_dir, fname)) for fname in re.findall(r"(\d+\.pq)", stdout)]
        return filenames

    @alru_cache
    async def read_simulation_chunks(self, experiment_id: str, namespace: Namespace) -> tuple[Path, pl.LazyFrame]:
        # TODO: instead use a session so as to not iteratively reauth
        local_chunks_dir = Path(await mkdtemp(dir="datamount", prefix=experiment_id))
        for chunkpath in await self.get_simulation_chunk_paths(experiment_id, namespace):
            local_fp = local_chunks_dir / chunkpath.parts[-1]
            await self.ssh_service.scp_download(local_file=local_fp, remote_path=chunkpath)

        return local_chunks_dir, self.scan_simulation_chunks(local_chunks_dir)

    @override
    async def close(self) -> None:
        pass
