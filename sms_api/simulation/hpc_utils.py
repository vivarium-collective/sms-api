import random
import string
import uuid
from pathlib import Path
from typing import Any

from sms_api.common.gateway.models import RouterConfig
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import get_settings
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDataset,
    SimulatorVersion,
)

VECOLI_REPO_NAME = "vEcoli"


def get_slurm_log_file(slurm_job_name: str) -> HPCFilePath:
    return get_settings().slurm_log_base_path / f"{slurm_job_name}.out"


def get_slurm_submit_file(slurm_job_name: str) -> HPCFilePath:
    return get_settings().slurm_log_base_path / f"{slurm_job_name}.sbatch"


def get_vEcoli_repo_dir(simulator_version: SimulatorVersion) -> HPCFilePath:
    return get_settings().hpc_repo_base_path / simulator_version.git_commit_hash / VECOLI_REPO_NAME


def get_parca_dataset_dirname(parca_dataset: ParcaDataset) -> str:
    git_commit_hash = parca_dataset.parca_dataset_request.simulator_version.git_commit_hash
    parca_id = parca_dataset.database_id
    return f"parca_{git_commit_hash}_id_{parca_id}"


def get_parca_dataset_dir(parca_dataset: ParcaDataset) -> HPCFilePath:
    parca_dataset_dirname = get_parca_dataset_dirname(parca_dataset)
    return get_settings().hpc_parca_base_path / parca_dataset_dirname


def get_experiment_path(ecoli_simulation: EcoliSimulation) -> HPCFilePath:
    sim_id = ecoli_simulation.database_id
    git_commit_hash = ecoli_simulation.sim_request.simulator.git_commit_hash
    experiment_dirname = f"experiment_{git_commit_hash}_id_{sim_id}"
    return get_settings().hpc_sim_base_path / experiment_dirname


def get_correlation_id(ecoli_simulation: EcoliSimulation, random_string: str) -> str:
    """
    Generate a correlation ID for the EcoliSimulation based on its database ID and git commit hash.
    """
    return f"{ecoli_simulation.database_id}_{ecoli_simulation.sim_request.simulator.git_commit_hash}_{random_string}"


def parse_correlation_id(correlation_id: str) -> tuple[int, str, str]:
    """
    Extract the simulation database ID and git commit hash from the correlation ID.
    """
    parts = correlation_id.split("_")
    if len(parts) != 3:
        raise ValueError(f"Invalid correlation ID format: {correlation_id}")
    simulation_id = int(parts[0])
    simulator_commit_hash = parts[1]
    random_string = parts[2]
    return simulation_id, simulator_commit_hash, random_string


def get_apptainer_image_file(simulator_version: SimulatorVersion) -> HPCFilePath:
    return get_settings().hpc_image_base_path / f"vecoli-{simulator_version.git_commit_hash}.sif"


def get_experiment_dirname(database_id: int, git_commit_hash: str) -> str:
    return f"experiment_{git_commit_hash}_id_{database_id}"


def format_experiment_path(experiment_dirname: str) -> HPCFilePath:
    base_path = HPCFilePath(remote_path=Path(f"/home/FCAM/svc_vivarium/{get_settings().namespace}/sims"))
    return base_path / experiment_dirname


def get_experiment_dirpath(simulation_database_id: int, git_commit_hash: str) -> HPCFilePath:
    experiment_dirname = get_experiment_dirname(database_id=simulation_database_id, git_commit_hash=git_commit_hash)
    return format_experiment_path(experiment_dirname=experiment_dirname)


def get_remote_chunks_dirpath(simulation_database_id: int, git_commit_hash: str) -> HPCFilePath:
    remote_dir_root = get_experiment_dirpath(
        simulation_database_id=simulation_database_id, git_commit_hash=git_commit_hash
    )
    experiment_dirname = remote_dir_root.name
    return (
        remote_dir_root
        / "history"
        / f"experiment_id={experiment_dirname}"
        / "variant=0"
        / "lineage_seed=0"
        / "generation=1"
        / "agent_id=0"
    )


def read_latest_commit() -> str:
    settings = get_settings()
    if not settings.assets_dir:
        raise ValueError("Assets directory is not set in the settings.")
    with open(Path(settings.assets_dir) / "simulation" / "model" / "latest_commit.txt") as f:
        return f.read().strip()


def get_experiment_id(
    router_config: RouterConfig, simulation: EcoliSimulation, sim_request: EcoliSimulationRequest
) -> str:
    return (
        router_config.prefix.replace("/", "")
        + "_"
        + get_experiment_dirname(simulation.database_id, sim_request.simulator.git_commit_hash)
    )


def add_variant_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    For Example:
     {
        "condition": {"condition": {"value":[ "basal", "with_aa", "acetate","succinate", "no_oxygen"]}}
    },
    """
    return config


def get_slurmjob_name(experiment_id: str, simulator_hash: str = "079c43c") -> str:
    random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))  # noqa: S311
    return f"sms-{simulator_hash}-{experiment_id}-{random_suffix}"


def get_experiment_dir(experiment_id: str) -> HPCFilePath:
    return get_settings().slurm_base_path / "workspace" / "outputs" / experiment_id


def create_experiment_id(config_id: str, simulator_hash: str) -> str:
    return f"{config_id}-{simulator_hash}-{str(uuid.uuid4()).split('-')[-1]}"
