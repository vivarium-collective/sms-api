import shutil
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from sms_api.common.hpc.sim_utils import get_single_simulation_chunks_dirpath
from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.simulation.hpc_utils import get_experiment_dirpath

main_branch = "master"
repo_url = "https://github.com/CovertLab/vEcoli"
latest_commit = "96bb7a2"
db_id = 1


@pytest.mark.asyncio
async def test_get_experiment_dirpath():
    experiment_dir = get_experiment_dirpath(db_id, latest_commit)
    assert experiment_dir == Path("/home/FCAM/svc_vivarium/test/sims/experiment_96bb7a2_id_1")


@pytest.mark.asyncio
async def test_get_chunks_dirpath(expected_columns):
    experiment_dir = Path("/home/FCAM/svc_vivarium/test/sims/experiment_96bb7a2_id_1_20250620-181422")
    chunk_id = 800
    results_fname = f"{chunk_id}.pq"

    # get remote dirpath
    remote_dirpath = get_single_simulation_chunks_dirpath(experiment_dir)
    remote_fpath = remote_dirpath / results_fname
    # make local mirror for temp
    local_dirpath = Path(tempfile.mkdtemp())
    local_fpath = local_dirpath / results_fname

    ssh_service = get_ssh_service()
    await ssh_service.scp_download(local_file=local_fpath, remote_path=remote_fpath)
    df = pd.read_parquet(local_fpath)

    assert df.columns.tolist() == expected_columns
    shutil.rmtree(local_dirpath)
