import logging

from fastapi import HTTPException

from sms_api.common import StrEnumBase
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    JobType,
    RegisteredSimulators,
    Simulator,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationService, SimulationServiceHpc

logger = logging.getLogger(__name__)


class RepoUrl(StrEnumBase):
    VECOLI_FORK_REPO_URL = "https://github.com/vivarium-collective/vEcoli"
    VECOLI_PUBLIC_REPO_URL = "https://github.com/CovertLab/vEcoli"
    VECOLI_PRIVATE_REPO_URL = ""


ACCEPTED_REPOS = {
    RepoUrl.VECOLI_FORK_REPO_URL: ["messages", "ccam-nextflow", "master"],
    RepoUrl.VECOLI_PUBLIC_REPO_URL: ["master", "ptools_viz"],
    RepoUrl.VECOLI_PRIVATE_REPO_URL: [],
}
DEFAULT_REPO = RepoUrl.VECOLI_PUBLIC_REPO_URL
DEFAULT_BRANCH = "master"


def verify_simulator_payload(simulator: Simulator) -> None:
    branch = simulator.git_branch
    url = simulator.git_repo_url
    match url:
        case RepoUrl.VECOLI_FORK_REPO_URL:
            accepted = ACCEPTED_REPOS[RepoUrl.VECOLI_FORK_REPO_URL]
            if branch not in accepted:
                raise ValueError(
                    f"{branch} is not an accepted branch for the {url} repo. Instead, use one of {accepted}"
                )
        case RepoUrl.VECOLI_PUBLIC_REPO_URL:
            accepted = ACCEPTED_REPOS[RepoUrl.VECOLI_PUBLIC_REPO_URL]
            if branch not in accepted:
                raise ValueError(
                    f"{branch} is not an accepted branch for the {url} repo. Instead, use one of {accepted}"
                )
    return None


async def get_latest_simulator(
    git_repo_url: str | None = None,
    git_branch: str = "messages",
) -> Simulator:
    "https://github.com/vivarium-collective/vEcoli"
    hpc_service = get_simulation_service()
    if hpc_service is None:
        logger.error("HPC service is not initialized")
        raise HTTPException(status_code=500, detail="HPC service is not initialized")

    try:
        latest_commit = await hpc_service.get_latest_commit_hash(git_branch=git_branch, git_repo_url=git_repo_url)
        return Simulator(git_commit_hash=latest_commit, git_repo_url=git_repo_url, git_branch=git_branch)
    except Exception as e:
        logger.exception("Error getting the latest simulator commit.")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def get_simulator_versions() -> RegisteredSimulators:
    sim_db_service = get_database_service()
    if sim_db_service is None:
        logger.error("Simulation database service is not initialized")
        raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
    try:
        simulators = await sim_db_service.list_simulators()
        return RegisteredSimulators(versions=simulators)
    except Exception as e:
        logger.exception("Error getting list of simulation versions")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def upload_simulator(
    commit_hash: str,
    git_repo_url: str,
    git_branch: str,
    simulation_service_slurm: SimulationService | SimulationServiceHpc | None = None,
    database_service: DatabaseService | None = None,
) -> SimulatorVersion:
    if not simulation_service_slurm:
        simulation_service_slurm = get_simulation_service()
    if simulation_service_slurm is None:
        logger.exception("Simulation service is not initialized")
        raise RuntimeError("Simulation service is not initialized")
    if not database_service:
        database_service = get_database_service()
    if database_service is None:
        logger.exception("Simulation database service is not initialized")
        raise RuntimeError("Simulation database service is not initialized")

    # check if the simulator version is already installed
    simulator: SimulatorVersion | None = None
    for _simulator in await database_service.list_simulators():
        if (
            _simulator.git_commit_hash == commit_hash
            and _simulator.git_repo_url == git_repo_url
            and _simulator.git_branch == git_branch
        ):
            simulator = _simulator
            break

    # insert the latest commit into the database and submit build job
    if simulator is None:
        simulator = await database_service.insert_simulator(
            git_commit_hash=commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )
        verify_simulator_payload(simulator)

        # Submit build job (which now includes cloning the repository)
        build_slurmjobid = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator)
        await database_service.insert_hpcrun(
            slurmjobid=build_slurmjobid,
            job_type=JobType.BUILD_IMAGE,
            ref_id=simulator.database_id,
            correlation_id="N/A",
        )

    return simulator
