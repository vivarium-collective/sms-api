import logging
import random
import string
import tempfile
from pathlib import Path
from textwrap import dedent

from typing_extensions import override

from sms_api.config import get_settings
from sms_api.dependencies import get_slurm_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import (
    get_apptainer_image_file,
    get_experiment_path,
    get_parca_dataset_dir,
    get_parca_dataset_dirname,
    get_slurm_log_file,
    get_slurm_submit_file,
    get_vEcoli_repo_dir,
)
from sms_api.simulation.models import EcoliSimulation, ParcaDataset, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SimulationServiceLocalHPC(SimulationService):
    _latest_commit_hash: str | None = None

    @override
    async def get_latest_commit_hash(
        self,
        git_repo_url: str = "https://github.com/vivarium-collective/vEcoli",
        git_branch: str = "messages",
    ) -> str:
        """
        :rtype: `str`
        :return: The last 7 characters of the latest commit hash.
        """
        assets_dir = get_settings().assets_dir
        latest_commit_file = Path(assets_dir) / "submodule_commit.txt"
        with open(latest_commit_file) as f:
            current_commit_hash = f.read().strip()
        return current_commit_hash

    @override
    async def clone_repository_if_needed(
        self,
        git_commit_hash: str,  # first 7 characters of the commit hash are used for the directory name
        git_repo_url: str = "https://github.com/vivarium-collective/vEcoli",
        git_branch: str = "messages",
    ) -> None:
        logger.warning("clone not needed for local HPC simulation service")

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        raise NotImplementedError()

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        raise NotImplementedError()

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: EcoliSimulation, database_service: DatabaseService, correlation_id: str
    ) -> int:
        settings = get_settings()
        if database_service is None:
            raise RuntimeError("DatabaseService is not available. Cannot submit EcoliSimulation job.")

        if ecoli_simulation.sim_request is None:
            raise ValueError("EcoliSimulation must have a sim_request set to submit a job.")

        parca_dataset = await database_service.get_parca_dataset(
            parca_dataset_id=ecoli_simulation.sim_request.parca_dataset_id
        )
        if parca_dataset is None:
            raise ValueError(f"ParcaDataset with ID {ecoli_simulation.sim_request.parca_dataset_id} not found.")

        slurm_service = get_slurm_service()
        simulator_version = parca_dataset.parca_dataset_request.simulator_version

        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))  # noqa: S311
        slurm_job_name = f"sim-{simulator_version.git_commit_hash}-{ecoli_simulation.database_id}-{random_suffix}"

        slurm_log_file = get_slurm_log_file(slurm_job_name=slurm_job_name)
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
        parca_dataset_path = get_parca_dataset_dir(parca_dataset=parca_dataset)
        parca_parent_path = parca_dataset_path.parent
        parca_dataset_dirname = get_parca_dataset_dirname(parca_dataset)
        experiment_path = get_experiment_path(ecoli_simulation=ecoli_simulation)
        experiment_path_parent = experiment_path.parent
        experiment_id = experiment_path.name
        hpc_sim_config_file = settings.hpc_sim_config_file
        remote_vEcoli_repo_path = get_vEcoli_repo_dir(simulator_version=simulator_version)
        apptainer_image_path = get_apptainer_image_file(simulator_version=simulator_version)

        # uv run --env-file .env ecoli/experiments/ecoli_master_sim.py \
        #             --generations 1 --emitter parquet --emitter_arg out_dir='out' \
        #             --experiment_id "parca_1" --daughter_outdir "out/parca_1" \
        #             --sim_data_path "out/parca_1/kb/simData.cPickle" ----fail_at_max_duration

        # build the submit script
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 2
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    #SBATCH --qos={settings.slurm_qos}
                    #SBATCH --output={slurm_log_file}
                    #SBATCH --nodelist={settings.slurm_node_list}

                    set -e
                    # env
                    mkdir -p {experiment_path_parent!s}

                    # check to see if the parca output directory is empty, if not, exit
                    if [ "$(ls -A {experiment_path!s})" ]; then
                        echo "Simulation output directory {experiment_path!s} is not empty. Skipping job."
                        exit 0
                    fi

                    commit_hash="{simulator_version.git_commit_hash}"
                    sim_id="{ecoli_simulation.database_id}"
                    echo "running simulation: commit=$commit_hash, simulation id=$sim_id on $(hostname) ..."

                    binds="-B {remote_vEcoli_repo_path!s}:/vEcoli"
                    binds+=" -B {parca_parent_path!s}:/parca"
                    binds+=" -B {experiment_path_parent!s}:/out"
                    image="{apptainer_image_path!s}"
                    cd {remote_vEcoli_repo_path!s}

                    # # scrape the slurm log file for the magic word and publish to NATS
                    # export NATS_URL={settings.nats_emitter_url}
                    # if [ -z "$NATS_URL" ]; then
                    #     echo "NATS_URL environment variable is not set."
                    # else
                    #     tail -F {slurm_log_file!s} | while read -r line; do
                    #         if echo "$line" | grep -q "{settings.nats_emitter_magic_word}"; then
                    #             clean_line="$(echo "$line" | sed \
                    #                -e 's/{settings.nats_emitter_magic_word}//g' \
                    #                -e "s/'/\\&quot;/g" )"
                    #             nats pub {settings.nats_worker_event_subject} "'$clean_line'"
                    #         fi
                    #     done &
                    #     SCRAPE_PID=$!
                    #     TAIL_PID=$(pgrep -P $SCRAPE_PID tail)
                    # fi

                    # create custom config file mapped to /out/configs/ directory
                    #  copy the template config file from the remote vEcoli repo
                    #  replace CORRELATION_ID_REPLACE_ME with the correlation_id
                    #
                    config_template_file={remote_vEcoli_repo_path!s}/configs/{hpc_sim_config_file}
                    mkdir -p {experiment_path_parent!s}/configs
                    config_file={experiment_path_parent!s}/configs/{hpc_sim_config_file}_{experiment_id}.json
                    cp $config_template_file $config_file
                    sed -i "s/CORRELATION_ID_REPLACE_ME/{correlation_id}/g" $config_file

                    git -C ./configs diff HEAD >> ./source-info/git_diff.txt
                    singularity run $binds $image uv run \\
                         --env-file /vEcoli/.env /vEcoli/ecoli/experiments/ecoli_master_sim.py \\
                         --config /out/configs/{hpc_sim_config_file}_{experiment_id}.json \\
                         --generations 1 --emitter parquet --emitter_arg out_dir='/out' \\
                         --experiment_id {experiment_id} \\
                         --daughter_outdir "/out/{experiment_id}" \\
                         --sim_data_path "/parca/{parca_dataset_dirname}/kb/simData.cPickle" \\
                         --fail_at_max_duration

                    # if [ -n "$SCRAPE_PID" ]; then
                    #     echo "Waiting for scrape to finish..."
                    #     sleep 10  # give time for the scrape to finish
                    #     kill $SCRAPE_PID || true  # kill the scrape process if it is still running
                    #     kill $TAIL_PID || true  # kill the tail process if it is still running
                    # else
                    #     echo "No scrape process found."
                    # fi

                    # if the experiment directory is empty after the run, fail the job
                    if [ ! "$(ls -A {experiment_path!s})" ]; then
                        echo "Simulation output directory {experiment_path!s} is empty. Job must have failed."
                        exit 1
                    fi

                    echo "Simulation run completed. data saved to {experiment_path!s}."
                    """)
                f.write(script_content)

            # submit the build script to slurm
            slurm_service = get_slurm_service()
            if slurm_service is None:
                raise RuntimeError("SlurmService is not available. Cannot submit EcoliSimulation job.")

            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def close(self) -> None:
        pass
