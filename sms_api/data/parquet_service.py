import logging
import os
import re
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import override

import polars as pl
from anyio import mkdtemp

from sms_api.common.gateway.utils import get_local_simulation_outdir, get_simulation_outdir
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import Settings, get_settings
from sms_api.simulation.hpc_utils import (
    get_remote_chunks_dirpath,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

assets_dir = Path(get_settings().assets_dir)
TEST_CHUNK_DIR = assets_dir / "tests" / "test_history"
TEST_CHUNK_PATH = TEST_CHUNK_DIR / "1200.pq"
TEST_EXPERIMENT_ID = "experiment_96bb7a2_id_1_20250620-181422"


def scan_simulation_chunks(chunks_dirpath: Path) -> pl.LazyFrame:
    return pl.scan_parquet(f"{chunks_dirpath!s}/*.pq", rechunk=True)


class ParquetService:
    settings: Settings

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_parquet_dir(
        self,
        experiment_id: str,
        variant: int | None = None,
        lineage_seed: int | None = None,
        generation: int | None = None,
        agent_id: int | None = None,
    ) -> Path:
        outdir = get_simulation_outdir(experiment_id)
        if outdir is None:
            logger.debug(f"{outdir} was requested but does not exist. Defaulting to local dir.")
            outdir = get_local_simulation_outdir(experiment_id=experiment_id)

        chunks_dir = outdir / "history"
        pq_dir = (
            chunks_dir
            / f"experiment_id={experiment_id}"
            / f"variant={variant or 0}"
            / f"lineage_seed={lineage_seed or 0}"
            / f"generation={generation or 1}"
            / f"agent_id={agent_id or 0}"
        )
        # if not pq_dir.exists():
        #     raise FileNotFoundError(f"Could not find parquet outputs at {pq_dir}")
        return pq_dir

    def get_parquet_path(
        self,
        experiment_id: str,
        chunk_id: int,
        variant: int | None = None,
        lineage_seed: int | None = None,
        generation: int | None = None,
        agent_id: int | None = None,
    ) -> Path:
        pq_dir = self.get_parquet_dir(experiment_id, variant, lineage_seed, generation, agent_id)
        pq_path = pq_dir / f"{chunk_id}.pq"
        if not pq_path.exists():
            raise FileNotFoundError(f"Could not find parquet output at {pq_path}")
        return pq_path

    def load_output_chunks(
        self,
        experiment_id: str,
        observables: list[str] | None = None,
        lazy: bool = False,
        variant: int | None = None,
        lineage_seed: int | None = None,
        generation: int | None = None,
        agent_id: int | None = None,
    ) -> pl.DataFrame | pl.LazyFrame:
        pq_dir = self.get_parquet_dir(experiment_id, variant, lineage_seed, generation, agent_id)
        lf = pl.scan_parquet(pq_dir)
        if lazy:
            return lf

        if observables:
            return lf.select(observables).collect()
        else:
            return lf.collect()


class RemoteParquetService(ABC):
    @abstractmethod
    def get_chunk_path(self, db_id: int, commit_hash: str, chunk_id: int) -> Path:
        pass

    @abstractmethod
    async def download_chunk(self, remote_chunk_path: Path, local_dirpath: Path | None = None) -> Path:
        pass

    @abstractmethod
    async def get_available_chunk_paths(self, experiment_id: str) -> list[HPCFilePath]:
        pass

    @abstractmethod
    async def read_lazy_chunks(self, experiment_id: str) -> tuple[Path, pl.LazyFrame]:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class ParquetServiceHpc(RemoteParquetService):
    @property
    def ssh_service(self) -> SSHService:
        return get_ssh_service()

    @override
    def get_chunk_path(self, db_id: int, commit_hash: str, chunk_id: int) -> HPCFilePath:
        results_fname = f"{chunk_id}.pq"

        # get remote dirpath
        remote_dirpath = get_remote_chunks_dirpath(db_id, commit_hash)
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

    async def get_available_chunk_paths(self, experiment_id: str, namespace: Namespace) -> list[Path]:
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

    async def read_lazy_chunks(self, experiment_id: str, namespace: Namespace) -> tuple[Path, pl.LazyFrame]:
        # TODO: instead use a session so as to not iteratively reauth
        local_chunks_dir = Path(await mkdtemp(dir="datamount", prefix=experiment_id))
        for chunkpath in await self.get_available_chunk_paths(experiment_id, namespace):
            local_fp = local_chunks_dir / chunkpath.parts[-1]
            await self.ssh_service.scp_download(local_file=local_fp, remote_path=chunkpath)

        return local_chunks_dir, scan_simulation_chunks(local_chunks_dir)

    async def close(self) -> None:
        pass
