from pathlib import Path

from sms_api.config import Settings, get_settings
from sms_api.simulation.models import EcoliSimulation, ParcaDataset, SimulatorVersion


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


def get_experiment_dirname(database_id: int, git_commit_hash: str) -> str:
    return f"experiment_{git_commit_hash}_id_{database_id}"


def format_experiment_path(settings: Settings, experiment_dirname: str) -> Path:
    return Path(settings.hpc_sim_base_path) / experiment_dirname


def get_experiment_path_from_database_id(database_id: int, git_commit_hash: str) -> Path:
    settings = get_settings()
    experiment_dirname = get_experiment_dirname(database_id=database_id, git_commit_hash=git_commit_hash)
    return format_experiment_path(settings, experiment_dirname)


def get_apptainer_image_file(simulator_version: SimulatorVersion) -> Path:
    settings = get_settings()
    hpc_image_remote_path = Path(settings.hpc_image_base_path)
    return hpc_image_remote_path / f"vecoli-{simulator_version.git_commit_hash}.sif"
