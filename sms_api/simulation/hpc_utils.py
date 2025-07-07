import os
from pathlib import Path

from sms_api.common.gateway.models import Namespace, RouterConfig
from sms_api.config import get_settings
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDataset,
    SimulatorVersion,
)


def get_slurm_log_file(slurm_job_name: str) -> Path:
    settings = get_settings()
    slurm_log_remote_path = Path(settings.slurm_log_base_path)
    return slurm_log_remote_path / f"{slurm_job_name}.out"


def get_slurm_submit_file(slurm_job_name: str) -> Path:
    settings = get_settings()
    slurm_log_remote_path = Path(settings.slurm_log_base_path)
    return slurm_log_remote_path / f"{slurm_job_name}.sbatch"


def get_vEcoli_repo_dir(simulator_version: SimulatorVersion) -> Path:
    settings = get_settings()
    return Path(settings.hpc_repo_base_path) / simulator_version.git_commit_hash / "vEcoli"


def get_parca_dataset_dirname(parca_dataset: ParcaDataset) -> str:
    git_commit_hash = parca_dataset.parca_dataset_request.simulator_version.git_commit_hash
    parca_id = parca_dataset.database_id
    return f"parca_{git_commit_hash}_id_{parca_id}"


def get_parca_dataset_dir(parca_dataset: ParcaDataset) -> Path:
    settings = get_settings()
    parca_dataset_dirname = get_parca_dataset_dirname(parca_dataset)
    return Path(settings.hpc_parca_base_path) / parca_dataset_dirname


def get_experiment_path(ecoli_simulation: EcoliSimulation) -> Path:
    settings = get_settings()
    sim_id = ecoli_simulation.database_id
    git_commit_hash = ecoli_simulation.sim_request.simulator.git_commit_hash
    experiment_dirname = f"experiment_{git_commit_hash}_id_{sim_id}"
    return Path(settings.hpc_sim_base_path) / experiment_dirname


def get_apptainer_image_file(simulator_version: SimulatorVersion) -> Path:
    settings = get_settings()
    hpc_image_remote_path = Path(settings.hpc_image_base_path)
    return hpc_image_remote_path / f"vecoli-{simulator_version.git_commit_hash}.sif"


def get_experiment_dirname(database_id: int, git_commit_hash: str) -> str:
    return f"experiment_{git_commit_hash}_id_{database_id}"


def format_experiment_path(experiment_dirname: str, namespace: Namespace = Namespace.TEST) -> Path:
    base_path = f"/home/FCAM/svc_vivarium/{namespace}/sims"
    return Path(base_path) / experiment_dirname


def get_experiment_dirpath(
    simulation_database_id: int, git_commit_hash: str, namespace: Namespace | None = None
) -> Path:
    experiment_dirname = get_experiment_dirname(database_id=simulation_database_id, git_commit_hash=git_commit_hash)
    return format_experiment_path(experiment_dirname=experiment_dirname, namespace=namespace or Namespace.TEST)


def get_remote_chunks_dirpath(
    simulation_database_id: int, git_commit_hash: str, namespace: Namespace | None = None
) -> Path:
    remote_dir_root = get_experiment_dirpath(
        simulation_database_id=simulation_database_id, git_commit_hash=git_commit_hash, namespace=namespace
    )
    experiment_dirname = str(remote_dir_root).split("/")[-1]
    return Path(
        os.path.join(
            remote_dir_root,
            "history",
            f"experiment_id={experiment_dirname}",
            "variant=0",
            "lineage_seed=0",
            "generation=1",
            "agent_id=0",
        )
    )


def read_latest_commit() -> str:
    with open("assets/latest_commit.txt") as f:
        return f.read().strip()


def get_experiment_id(
    router_config: RouterConfig, simulation: EcoliSimulation, sim_request: EcoliSimulationRequest
) -> str:
    return (
        router_config.prefix.replace("/", "")
        + "_"
        + get_experiment_dirname(simulation.database_id, sim_request.simulator.git_commit_hash)
    )
