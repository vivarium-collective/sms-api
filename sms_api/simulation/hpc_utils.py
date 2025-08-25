import os
from pathlib import Path
from textwrap import dedent

from sms_api.common.gateway.models import Namespace, RouterConfig
from sms_api.config import Settings, get_settings
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDataset,
    SimulatorVersion,
)

VECOLI_REPO_NAME = "vEcoli"


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
    return Path(settings.hpc_repo_base_path) / simulator_version.git_commit_hash / VECOLI_REPO_NAME


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


def build_workflow_sbatch(
    slurm_job_name: str,
    settings: Settings,
    ecoli_simulation: EcoliSimulation,
    slurm_log_file: Path,
    correlation_id: str,
    parca_parent_path: Path,
    image_path: Path | None = None,
    namespace: Namespace | None = None,
) -> str:
    """
    - simulator_version commit hash latest: 78c6310
    - remote basepath: /home/FCAM/svc_vivarium
    - vecoli_dir: /home/FCAM/svc_vivarium/prod/repos/78c6310/vEcoli
    """
    request = ecoli_simulation.sim_request
    simulator_version = request.simulator
    simulator_hash = simulator_version.git_commit_hash
    config_id = request.config_id or "sms_single"

    # define paths
    basepath = Path(settings.slurm_base_path)
    deployment_path = Path(f"{basepath}/{namespace or Namespace.PRODUCTION}")

    remote_vecoli_dir = deployment_path / f"repos/{simulator_hash}/vEcoli"
    apptainer_path = image_path or deployment_path / f"images/vecoli-{simulator_hash}.sif"
    config_fp = remote_vecoli_dir / f"configs/{config_id}.json"
    experiment_fp = get_experiment_path(ecoli_simulation=ecoli_simulation)
    experiment_id = experiment_fp.name
    experiment_parent_fp = experiment_fp.parent
    hpc_sim_config_file = settings.hpc_sim_config_file

    vecoli_dir, img_path, config_path, log_path, experiment_path_parent, experiment_path = [
        fp.__str__()
        for fp in [remote_vecoli_dir, apptainer_path, config_fp, slurm_log_file, experiment_parent_fp, experiment_fp]
    ]

    return dedent(f"""\
    #!/bin/bash
    #SBATCH --job-name={slurm_job_name}
    #SBATCH --time=30:00
    #SBATCH --cpus-per-task 2
    #SBATCH --mem=8GB
    #SBATCH --partition={settings.slurm_partition}
    #SBATCH --qos={settings.slurm_qos}
    #SBATCH --output={slurm_log_file!s}
    #SBATCH --nodelist={settings.slurm_node_list}

    set -e

    # TODO: we probably want/have to change this for generalization
    # load nextflow
    module load nextflow

    mkdir -p {experiment_path_parent!s}
    if [ "$(ls -A {experiment_path!s})" ]; then
        echo "Simulation output directory {experiment_path!s} is not empty. Skipping job."
        exit 0
    fi

    binds="-B {vecoli_dir!s}:/vEcoli"
    binds+=" -B {parca_parent_path!s}:/parca"
    binds+=" -B {experiment_path_parent!s}:/out"
    image="{apptainer_path!s}"
    cd {vecoli_dir!s}

    # cd {vecoli_dir}
    # srun runscripts/container/interactive.sh -i {img_path} \
    # -a -c "python runscripts/workflow.py --config {config_path}"

    config_template_file={vecoli_dir!s}/configs/{hpc_sim_config_file}
    mkdir -p {experiment_path_parent!s}/configs
    config_file={experiment_path_parent!s}/configs/{hpc_sim_config_file}_{experiment_id}.json
    cp $config_template_file $config_file
    sed -i "s/CORRELATION_ID_REPLACE_ME/{correlation_id}/g" $config_file
    git -C ./configs diff HEAD >> ./source-info/git_diff.txt

    singularity run $binds $image uv run \\
        /vEcoli/runscripts/workflow.py \\
        --config /out/configs/{hpc_sim_config_file}_{experiment_id}.json

    if [ ! "$(ls -A {experiment_path!s})" ]; then
        echo "Simulation output directory {experiment_path!s} is empty. Job must have failed."
        exit 1
    fi
    echo "Simulation run completed. data saved to {experiment_path!s}."
    """)
