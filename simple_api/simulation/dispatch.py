"""
Gateway dispatcher. This module provides the following logic:

a. A way to validate jobs (ensure not garbage-in)
b. A way to actually run the simulation workflow (clone, dbio, run, etc)
c. A way to read the data as required for /get-results.
"""

import asyncio
import os
import shutil
import tempfile
import time
from pathlib import Path

from simple_api.common.hpc.models import SlurmJob
from simple_api.common.hpc.sim_utils import get_single_simulation_chunks_dirpath, read_latest_commit
from simple_api.config import get_settings
from simple_api.simulation.database_service import SimulationDatabaseService
from simple_api.simulation.hpc_utils import format_experiment_path, get_experiment_dirname
from simple_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDatasetRequest,
    SimulatorHash,
    SimulatorVersion,
)
from simple_api.simulation.simulation_service import SimulationService, SimulationServiceHpc

main_branch = "master"
repo_url = "https://github.com/CovertLab/vEcoli"
latest_commit_hash = read_latest_commit()


def validate_job(job: SlurmJob | None) -> None:
    if job is not None:
        if not job.is_done():
            raise Exception("Job is not yet done.")
    else:
        raise Exception("Could not find job.")
    return


# TODO: Create a new SQL Model/ORM representing a Table called status:
# Then at the completetion (or even start) of each polling block below,
# update row status
async def run_simulation(
    simulation_service: SimulationService,
    database_service: SimulationDatabaseService,
    total_time: float | None = None,
) -> tuple[EcoliSimulation, int]:
    """
    Submit a single whole-cell-model vEcoli simulation request to the HPC and run the entire
        workflow (including parca if needed) for the specified duration.
    """
    # check if the latest commit is already installed
    simulator: SimulatorVersion | None = None
    for _simulator in await database_service.list_simulators():
        if (
            _simulator.git_commit_hash == latest_commit_hash
            and _simulator.git_repo_url == repo_url
            and _simulator.git_branch == main_branch
        ):
            simulator = _simulator
            break

    # insert the latest commit into the database
    if simulator is None:
        simulator = await database_service.insert_simulator(
            git_commit_hash=latest_commit_hash, git_repo_url=repo_url, git_branch=main_branch
        )

    # clone the repository if needed
    _hash: str | SimulatorHash = simulator.git_commit_hash
    await simulation_service.clone_repository_if_needed(
        git_commit_hash=_hash.latest_commit if isinstance(_hash, SimulatorHash) else _hash,
        git_repo_url=simulator.git_repo_url,
        git_branch=simulator.git_branch,
    )

    # build the image
    build_job_id = await simulation_service.submit_build_image_job(simulator_version=simulator)

    if build_job_id is None:
        raise Exception(f"Could not submit simulation with the simulator:\n{simulator.model_dump_json()}")

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_build = await simulation_service.get_slurm_job_status(slurmjobid=build_job_id)
        if slurm_job_build is not None and slurm_job_build.is_done():
            break
        await asyncio.sleep(5)
    validate_job(slurm_job_build)

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config={"param1": 5})
    parca_dataset = await database_service.get_or_insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    # run parca
    parca_job_id = await simulation_service.submit_parca_job(parca_dataset=parca_dataset)

    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_parca = await simulation_service.get_slurm_job_status(slurmjobid=parca_job_id)
        if slurm_job_parca is not None and slurm_job_parca.is_done():
            break
        await asyncio.sleep(5)
    validate_job(slurm_job_parca)

    # create new simulation instance by inserting it into the db (not yet submitted to hpc)
    simulation_request = EcoliSimulationRequest(
        simulator=simulator,
        parca_dataset_id=parca_dataset.database_id,
        variant_config={"named_parameters": {"param1": 0.5, "param2": 0.5}},
    )
    if total_time:
        simulation_request.total_time = total_time
    simulation = await database_service.insert_simulation(sim_request=simulation_request)

    # actually submit the simulation to the hpc and return an indexable sim job id
    sim_job_id = await simulation_service.submit_ecoli_simulation_job(
        ecoli_simulation=simulation, simulation_database_service=database_service
    )

    return simulation, sim_job_id


async def poll_slurm_job(simulation_service_slurm: SimulationServiceHpc, sim_job_id: int) -> None:
    # poll for job status
    start_time = time.time()
    while start_time + 60 > time.time():
        slurm_job_sim = await simulation_service_slurm.get_slurm_job_status(slurmjobid=sim_job_id)
        if slurm_job_sim is not None and slurm_job_sim.is_done():
            break
        await asyncio.sleep(5)

    validate_job(slurm_job_sim)


async def read_chunks(simulation: EcoliSimulation, remove_local: bool = False) -> Path:
    """
    NOTE: This function assumes that the request associated with `simulation`
        has already been submitted AND has at least some results ready.

    :param simulation: (`EcoliSimulation`) Simulation instance whose request has already been submitted.
    :param remove_local: (`bool`) If `True`, delete the local dir containing the downloaded
        chunk files. Defaults to `False`.

    :rtype: `pathlib.Path`
    :return: Local dirpath containg the downloaded chunk files.
    """
    ssh_settings = get_settings()
    # ssh_service = get_ssh_service(settings=ssh_settings)

    # extract experiment dir and create a local mirror for download dest
    experiment_dirname = get_experiment_dirname(simulation.database_id, latest_commit_hash)
    experiment_dir_root = format_experiment_path(ssh_settings, experiment_dirname)

    remote_dirpath: Path = get_single_simulation_chunks_dirpath(
        experiment_dir_root
    )  # eg: experiment_dirname/'experiment=....', etc
    local_dirpath: Path = Path(tempfile.mkdtemp(suffix=experiment_dirname))

    # get available chunk files
    available_chunk_paths: list[Path] = [
        Path(os.path.join(remote_dirpath, fname)) for fname in os.listdir(remote_dirpath) if fname.endswith(".pq")
    ]

    if not len(available_chunk_paths):
        raise Exception(f"There are no chunk files available for {experiment_dirname}")

    # for each chunk:
    #   remote_fp = pathjoin(remote_dirpath, chunkfile)
    #   local_fp = pathjoin(local_dirpath, chunkfile)
    #   hpc_service.scp_download(remote_fp, local_fp)

    if remove_local:
        shutil.rmtree(local_dirpath)
        print("""
            Removing local dir containing the files you just downloaded.! \
            The path returned by this function will not exist and be for record keeping only!
        """)

    return Path(local_dirpath)
