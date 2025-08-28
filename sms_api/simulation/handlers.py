import logging
import random
import string

from fastapi import BackgroundTasks, HTTPException

from sms_api.common.gateway.models import RouterConfig
from sms_api.dependencies import get_database_service, get_simulation_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import get_correlation_id, get_experiment_id
from sms_api.simulation.models import (
    EcoliExperiment,
    EcoliSimulationRequest,
    EcoliSimulationWorkflow,
    EcoliWorkflowRequest,
    JobType,
    ParcaDataset,
    ParcaDatasetRequest,
    RegisteredSimulators,
    Simulator,
    SimulatorVersion,
)
from sms_api.simulation.simulation_service import SimulationService, SimulationServiceHpc

logger = logging.getLogger(__name__)

# -- roundtrip job handlers that both call the services and return the relative endpoint's DTO -- #


def verify_simulator_payload(simulator: Simulator) -> None:
    if simulator.git_repo_url not in [
        "https://github.com/vivarium-collective/vEcoli",
        "https://github.com/CovertLab/vEcoli",
    ]:
        raise HTTPException(status_code=404, detail="You may not upload a simulator from any other source.")
    # if not simulator.git_branch == "messages":
    #     raise HTTPException(
    #         status_code=404, detail="You must be authorized to upload a simulator from any branch other than main."
    #     )


async def get_latest_simulator(
    git_repo_url: str = "https://github.com/vivarium-collective/vEcoli",
    git_branch: str = "messages",
) -> Simulator:
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
    background_tasks: BackgroundTasks | None = None,
) -> SimulatorVersion:
    if not simulation_service_slurm:
        simulation_service_slurm = get_simulation_service()
    if simulation_service_slurm is None:
        logger.exception("Simulation service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation service is not initialized")
    if not database_service:
        database_service = get_database_service()
    if database_service is None:
        logger.exception("Simulation database service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation database service is not initialized")

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

    # insert the latest commit into the database
    if simulator is None:
        simulator = await database_service.insert_simulator(
            git_commit_hash=commit_hash, git_repo_url=git_repo_url, git_branch=git_branch
        )

        async def dispatch_job() -> None:
            # clone the repository if needed
            await simulation_service_slurm.clone_repository_if_needed(
                git_commit_hash=simulator.git_commit_hash,
                git_repo_url=simulator.git_repo_url,
                git_branch=simulator.git_branch,
            )
            # build the image
            build_slurmjobid = await simulation_service_slurm.submit_build_image_job(simulator_version=simulator)
            await database_service.insert_hpcrun(
                slurmjobid=build_slurmjobid,
                job_type=JobType.BUILD_IMAGE,
                ref_id=simulator.database_id,
                correlation_id="N/A",
            )

        if background_tasks is not None:
            background_tasks.add_task(dispatch_job)
        else:
            await dispatch_job()

    return simulator


async def run_parca(
    simulator: SimulatorVersion,
    simulation_service_slurm: SimulationService | None = None,
    database_service: DatabaseService | None = None,
    parca_config: dict[str, int | float | str] | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> ParcaDataset:
    if not simulation_service_slurm:
        simulation_service_slurm = get_simulation_service()
    if simulation_service_slurm is None:
        logger.exception("Simulation service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation service is not initialized")
    if not database_service:
        database_service = get_database_service()
    if database_service is None:
        logger.exception("Simulation database service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation database service is not initialized")

    parca_dataset_request = ParcaDatasetRequest(simulator_version=simulator, parca_config=parca_config or {})
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    async def dispatch_job() -> None:
        # run parca
        parca_slurmjobid = await simulation_service_slurm.submit_parca_job(parca_dataset=parca_dataset)
        _hpc_run = await database_service.insert_hpcrun(
            slurmjobid=parca_slurmjobid,
            job_type=JobType.PARCA,
            ref_id=parca_dataset.database_id,
            correlation_id="N/A",
        )

    # submit run parca
    if background_tasks is not None:
        background_tasks.add_task(dispatch_job)
    else:
        await dispatch_job()
    return parca_dataset


async def get_parca_datasets(
    simulation_service_slurm: SimulationService | None = None,
    database_service: DatabaseService | None = None,
) -> list[ParcaDataset]:
    if not simulation_service_slurm:
        simulation_service_slurm = get_simulation_service()
    if simulation_service_slurm is None:
        logger.exception("Simulation service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation service is not initialized")
    if not database_service:
        database_service = get_database_service()
    if database_service is None:
        logger.exception("Simulation database service is not initialized")
        raise HTTPException(status_code=404, detail="Simulation database service is not initialized")

    parca_datasets = await database_service.list_parca_datasets()
    return parca_datasets


async def run_simulation(
    simulator: SimulatorVersion,
    parca_dataset_id: int,
    database_service: DatabaseService,
    simulation_service_slurm: SimulationService,
    router_config: RouterConfig,
    variant_config: dict[str, dict[str, int | float | str]] | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> EcoliExperiment:
    simulation_request = EcoliSimulationRequest(
        simulator=simulator,
        parca_dataset_id=parca_dataset_id,
        variant_config=variant_config or {"named_parameters": {"param1": 0.5, "param2": 0.5}},
    )
    simulation = await database_service.insert_simulation(sim_request=simulation_request)

    async def dispatch_job() -> None:
        random_string_7_hex = "".join(random.choices(string.hexdigits, k=7))  # noqa: S311 doesn't need to be secure
        correlation_id = get_correlation_id(ecoli_simulation=simulation, random_string=random_string_7_hex)
        sim_slurmjobid = await simulation_service_slurm.submit_ecoli_simulation_job(
            ecoli_simulation=simulation, database_service=database_service, correlation_id=correlation_id
        )
        _hpcrun = await database_service.insert_hpcrun(
            slurmjobid=sim_slurmjobid,
            job_type=JobType.SIMULATION,
            ref_id=simulation.database_id,
            correlation_id=correlation_id,
        )

    if background_tasks:
        background_tasks.add_task(dispatch_job)
    else:
        await dispatch_job()
    experiment_id = get_experiment_id(
        router_config=router_config, simulation=simulation, sim_request=simulation_request
    )

    return EcoliExperiment(experiment_id=experiment_id, simulation=simulation)


async def run_workflow(
    simulation_request: EcoliWorkflowRequest,
    database_service: DatabaseService,
    simulation_service_slurm: SimulationService,
    router_config: RouterConfig,
    background_tasks: BackgroundTasks | None = None,
) -> EcoliExperiment:
    # simulation = await database_service.insert_simulation(sim_request=simulation_request)
    simulation = EcoliSimulationWorkflow(sim_request=simulation_request)

    async def dispatch_job() -> None:
        random_string_7_hex = "".join(random.choices(string.hexdigits, k=7))  # noqa: S311 doesn't need to be secure
        correlation_id = get_correlation_id(ecoli_simulation=simulation, random_string=random_string_7_hex)
        sim_slurmjobid = await simulation_service_slurm.submit_vecoli_job(
            ecoli_simulation=simulation, database_service=database_service
        )
        _hpcrun = await database_service.insert_hpcrun(
            slurmjobid=sim_slurmjobid,
            job_type=JobType.SIMULATION,
            ref_id=simulation.database_id,
            correlation_id=correlation_id,
        )

    if background_tasks:
        background_tasks.add_task(dispatch_job)
    else:
        await dispatch_job()
    experiment_id = get_experiment_id(
        router_config=router_config, simulation=simulation, sim_request=simulation_request
    )

    return EcoliExperiment(experiment_id=experiment_id, simulation=simulation)
