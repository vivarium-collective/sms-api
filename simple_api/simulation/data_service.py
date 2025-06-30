import asyncio
import logging
import random
import shutil
import string
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent

import pandas as pd
from typing_extensions import override

from simple_api.common.hpc.models import SlurmJob
from simple_api.common.hpc.sim_utils import get_single_simulation_chunks_dirpath, read_latest_commit
from simple_api.common.hpc.slurm_service import SlurmService
from simple_api.common.ssh.ssh_service import SSHService, get_ssh_service
from simple_api.config import Settings, get_settings
from simple_api.simulation.db_service import SimulationDatabaseService
from simple_api.simulation.hpc_utils import (
    get_apptainer_image_file,
    get_experiment_path,
    get_parca_dataset_dir,
    get_parca_dataset_dirname,
    get_remote_chunks_dirpath,
    get_slurm_log_file,
    get_slurm_submit_file,
    get_vEcoli_repo_dir,
)
from simple_api.simulation.models import EcoliSimulation, Namespaces, ParcaDataset, SimulatorVersion

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DataService(ABC):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
    
    @abstractmethod
    def get_ssh_service(self):
        pass
    
    @abstractmethod
    def get_chunk_path(self, db_id: int, commit_hash: str, chunk_id: int, namespace: Namespaces | None = None):
        pass

    @abstractmethod
    async def get_chunk_data(self, remote_chunk_path: Path) -> pd.DataFrame:
        pass


class DataServiceHpc(DataService):
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
    
    @override
    def get_ssh_service(self):
        return get_ssh_service(self.settings)
    
    @override
    def get_chunk_path(self, db_id: int, commit_hash: str, chunk_id: int, namespace: Namespaces | None = None) -> Path:
        results_fname = f"{chunk_id}.pq"

        # get remote dirpath
        remote_dirpath = get_remote_chunks_dirpath(db_id, commit_hash, namespace or Namespaces.TEST)
        return remote_dirpath / results_fname
    
    @override 
    async def get_chunk_data(self, remote_chunk_path: Path) -> pd.DataFrame:
        # make local mirror for temp
        results_fname = str(remote_chunk_path).split('/')[-1]
        local_dirpath = Path(tempfile.mkdtemp())
        local_fpath = local_dirpath / results_fname
        ssh_service = self.get_ssh_service()
        await ssh_service.scp_download(local_file=local_fpath, remote_path=remote_chunk_path)

        df = pd.read_parquet(local_fpath)
        shutil.rmtree(local_dirpath)
        return df


async def test_get_chunk_path():
    db_id = 1
    commit = read_latest_commit()
    chunk_id = 800
    service = DataServiceHpc()
    remote_path = service.get_chunk_path(db_id, commit, chunk_id)
    await service.get_chunk_data(remote_path)


async def test_get_chunk_data():
    service = DataServiceHpc()
    remote_path = get_single_simulation_chunks_dirpath(
        Path("/home/FCAM/svc_vivarium/test/sims/experiment_96bb7a2_id_1_20250620-181422")
    )
    df = await service.get_chunk_data(remote_path / "800.pq")
    print(df)


if __name__ == "__main__":
    asyncio.run(test_get_chunk_data())
