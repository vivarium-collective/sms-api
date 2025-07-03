import os
from pathlib import Path

from sms_api.config import get_settings
from sms_api.simulation.models import EcoliSimulation, Namespaces, ParcaDataset, SimulatorVersion


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


def get_experiment_path_from_database_id(database_id: int, git_commit_hash: str) -> Path:
    settings = get_settings()
    experiment_dirname = get_experiment_dirname(database_id=database_id, git_commit_hash=git_commit_hash)
    return format_experiment_path(experiment_dirname)


def get_apptainer_image_file(simulator_version: SimulatorVersion) -> Path:
    settings = get_settings()
    hpc_image_remote_path = Path(settings.hpc_image_base_path)
    return hpc_image_remote_path / f"vecoli-{simulator_version.git_commit_hash}.sif"


def get_experiment_dirname(database_id: int, git_commit_hash: str) -> str:
    return f"experiment_{git_commit_hash}_id_{database_id}"


def format_experiment_path(experiment_dirname: str, namespace: Namespaces = Namespaces.TEST) -> Path:
    base_path = f"/home/FCAM/svc_vivarium/{namespace}/sims"
    return Path(base_path) / experiment_dirname


def get_experiment_dirpath(
    simulation_database_id: int, git_commit_hash: str, namespace: Namespaces | None = None
) -> Path:
    """
    Get the REMOTE PARENT (outermost) dirpath from the hpc for a given experiment. This dirpath is assumed to be in the HPC under
        ~/<NAMESPACE>/experiment_..... and should contain the redundant vEcoli results paths (experiment=.../variant=.../...). For example,
        a hash of 123456a and db id of 2 in the test namespace will return:
            `fp = /home/FCAM/svc_vivarium/test/sims/experiment_123456a_2`.
        Here, `fp` must contain the following path:
            `/home/FCAM/svc_vivarium/test/sims/experiment_123456a_2/history/experiment_id=experiment_123456a_2/variant=1/lineage_seed=0/generation=1/agent_id=1`
            and this path itself should be the innermost directory containing all of the simulation run's parquet files.

    :param simulation_database_id: (`int`) database ID for the given simulation. TODO: replace this with a better primary key
    :param git_commit_hash: (`str`) Last 7 characters of the commit hash for the simulator version used to run the simulation.
    :param namespace: (`Namespaces`) Namespace used to store the results in HPC. Choose one of: prod, test, dev. Defaults to `test`.
    """
    experiment_dirname = get_experiment_dirname(database_id=simulation_database_id, git_commit_hash=git_commit_hash)
    return format_experiment_path(experiment_dirname=experiment_dirname, namespace=namespace or Namespaces.TEST)


def get_remote_chunks_dirpath(
    simulation_database_id: int, git_commit_hash: str, namespace: Namespaces | None = None
) -> Path:
    """
    Obtains the absolute path to the innermost dirpath child in which `.pq` chunk files are stored for a given single (WCM)
        simulation on the HPC.

    :param simulation_database_id: (`int`) database ID for the given simulation. TODO: replace this with a better primary key
    :param git_commit_hash: (`str`) Last 7 characters of the commit hash for the simulator version used to run the simulation.
    :param namespace: (`Namespaces`) Namespace used to store the results in HPC. Choose one of: prod, test, dev. Defaults to `test`.
    """
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
