import logging
import random
import string
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent

from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import (
    VECOLI_REPO_NAME,
    get_apptainer_image_file,
    get_experiment_path,
    get_parca_dataset_dir,
    get_parca_dataset_dirname,
    get_slurm_log_file,
    get_slurm_submit_file,
    get_vEcoli_repo_dir,
)
from sms_api.simulation.models import EcoliSimulation, ParcaDataset, SimulatorVersion

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SimulationService(ABC):
    @abstractmethod
    async def get_latest_commit_hash(
        self,
        ssh_service: SSHService | None = None,
        git_repo_url: str = "https://github.com/CovertLab/vEcoli",
        git_branch: str = "master",
    ) -> str:
        pass

    @abstractmethod
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        pass

    @abstractmethod
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        pass

    @abstractmethod
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: EcoliSimulation, database_service: DatabaseService
    ) -> int:
        pass

    @abstractmethod
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        pass

    @abstractmethod
    async def clone_repository_if_needed(
        self,
        git_commit_hash: str,  # first 7 characters of the commit hash are used for the directory name
        git_repo_url: str = "https://github.com/vivarium-collective/vEcoli",
        git_branch: str = "messages",
    ) -> None:
        """
        Clone a git repository to a remote directory and return the path to the cloned repository.
        :param git_commit_hash: The commit hash to checkout after cloning.
        :param repo_url: The URL of the git repository to clone.
        :param branch: The branch to clone.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class SimulationServiceHpc(SimulationService):
    _latest_commit_hash: str | None = None

    @override
    async def get_latest_commit_hash(
        self,
        ssh_service: SSHService | None = None,
        git_repo_url: str = "https://github.com/vivarium-collective/vEcoli",
        git_branch: str = "messages",
    ) -> str:
        """
        :rtype: `str`
        :return: The last 7 characters of the latest commit hash.
        """
        svc = ssh_service or get_ssh_service()
        return_code, stdout, stderr = await svc.run_command(f"git ls-remote -h {git_repo_url} {git_branch}")
        if return_code != 0:
            raise RuntimeError(f"Failed to list git commits for repository: {stderr.strip()}")
        latest_commit_hash = stdout.strip("\n")[:7]
        assets_dir = get_settings().assets_dir
        with open(Path(assets_dir) / "latest_commit.txt", "w") as f:
            f.write(latest_commit_hash)

        self._latest_commit_hash = latest_commit_hash
        return latest_commit_hash

    @override
    async def clone_repository_if_needed(
        self,
        git_commit_hash: str,  # first 7 characters of the commit hash are used for the directory name
        git_repo_url: str = "https://github.com/vivarium-collective/vEcoli",
        git_branch: str = "messages",
    ) -> None:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )

        software_version_path = Path(settings.hpc_repo_base_path) / git_commit_hash
        test_cmd = f"test -d {software_version_path!s}"
        dir_cmd = f"mkdir -p {software_version_path!s} && cd {software_version_path!s}"
        clone_cmd = f"git clone --branch {git_branch} --single-branch {git_repo_url} {VECOLI_REPO_NAME}"
        # skip if directory exists, otherwise create it and clone the repo
        command = f"{test_cmd} || ({dir_cmd} && {clone_cmd} && cd {VECOLI_REPO_NAME} && git checkout {git_commit_hash})"
        return_code, stdout, stderr = await ssh_service.run_command(command=command)
        if return_code != 0:
            raise RuntimeError(
                f"Failed to clone repo {git_repo_url} branch {git_branch} hash {git_commit_hash}: {stderr.strip()}"
            )

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        slurm_service = SlurmService(ssh_service=ssh_service)

        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))  # noqa: S311
        slurm_job_name = f"build-image-{simulator_version.git_commit_hash}-{random_suffix}"

        slurm_log_file = get_slurm_log_file(slurm_job_name=slurm_job_name)
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
        remote_vEcoli_path = get_vEcoli_repo_dir(simulator_version=simulator_version)
        apptainer_image_path = get_apptainer_image_file(simulator_version=simulator_version)

        remote_build_script_relative_path = Path("runscripts") / "container" / "build-image.sh"

        # build the submit script
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                build_image_cmd = f"{remote_build_script_relative_path!s} -i {apptainer_image_path!s} -a"
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 2
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    #SBATCH --qos={settings.slurm_qos}
                    #SBATCH --wait
                    #SBATCH --output={slurm_log_file}
                    #SBATCH --nodelist={settings.slurm_node_list}

                    set -e
                    env
                    mkdir -p {apptainer_image_path.parent!s}

                    # if the image already exists, skip the build
                    if [ -f {apptainer_image_path!s} ]; then
                        echo "Image {apptainer_image_path!s} already exists. Skipping build."
                        exit 0
                    fi

                    echo "Building vEcoli image for commit {simulator_version.git_commit_hash} on $(hostname) ..."

                    cd {remote_vEcoli_path!s}
                    {build_image_cmd}

                    # if the image does not exist after the build, fail the job
                    if [ ! -f {apptainer_image_path!s} ]; then
                        echo "Image build failed. Image not found at {apptainer_image_path!s}."
                        exit 1
                    fi

                    echo "Build completed. Image saved to {apptainer_image_path!s}."
                    """)
                f.write(script_content)

            # submit the build script to slurm
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        slurm_service = SlurmService(ssh_service=ssh_service)
        simulator_version = parca_dataset.parca_dataset_request.simulator_version

        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))  # noqa: S311
        slurm_job_name = f"parca-{simulator_version.git_commit_hash}-{parca_dataset.database_id}-{random_suffix}"

        slurm_log_file = get_slurm_log_file(slurm_job_name=slurm_job_name)
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
        parca_remote_path = get_parca_dataset_dir(parca_dataset=parca_dataset)
        remote_vEcoli_repo_path = get_vEcoli_repo_dir(simulator_version=simulator_version)
        apptainer_image_path = get_apptainer_image_file(simulator_version=simulator_version)

        # build the submit script
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 3
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    #SBATCH --qos={settings.slurm_qos}
                    #SBATCH --wait
                    #SBATCH --output={slurm_log_file}
                    #SBATCH --nodelist={settings.slurm_node_list}

                    set -e
                    # env
                    mkdir -p {parca_remote_path!s}

                    # check to see if the parca output directory is empty, if not, exit
                    if [ "$(ls -A {parca_remote_path!s})" ]; then
                        echo "Parca output directory {parca_remote_path!s} is not empty. Skipping job."
                        exit 0
                    fi

                    commit_hash="{simulator_version.git_commit_hash}"
                    parca_id="{parca_dataset.database_id}"
                    echo "running parca: commit=$commit_hash, parca id=$parca_id on $(hostname) ..."

                    binds="-B {remote_vEcoli_repo_path!s}:/vEcoli -B {parca_remote_path!s}:/parca_out"
                    image="{apptainer_image_path!s}"
                    cd {remote_vEcoli_repo_path!s}
                    singularity run $binds $image uv run \\
                         --env-file /vEcoli/.env /vEcoli/runscripts/parca.py \\
                         --config /vEcoli/configs/run_parca.json -c 3 -o /parca_out

                    # if the parca directory is empty after the run, fail the job
                    if [ ! "$(ls -A {parca_remote_path!s})" ]; then
                        echo "Parca output directory {parca_remote_path!s} is empty. Job must have failed."
                        exit 1
                    fi

                    echo "Parca run completed. data saved to {parca_remote_path!s}."
                    """)
                f.write(script_content)

            # submit the build script to slurm
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: EcoliSimulation, database_service: DatabaseService
    ) -> int:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        if database_service is None:
            raise RuntimeError("DatabaseService is not available. Cannot submit EcoliSimulation job.")

        if ecoli_simulation.sim_request is None:
            raise ValueError("EcoliSimulation must have a sim_request set to submit a job.")

        parca_dataset = await database_service.get_parca_dataset(
            parca_dataset_id=ecoli_simulation.sim_request.parca_dataset_id
        )
        if parca_dataset is None:
            raise ValueError(f"ParcaDataset with ID {ecoli_simulation.sim_request.parca_dataset_id} not found.")

        slurm_service = SlurmService(ssh_service=ssh_service)
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
                    #SBATCH --wait
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

                    git -C ./configs diff HEAD >> ./source-info/git_diff.txt
                    singularity run $binds $image uv run \\
                         --env-file /vEcoli/.env /vEcoli/ecoli/experiments/ecoli_master_sim.py \\
                         --config /vEcoli/configs/{hpc_sim_config_file} \\
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
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        slurm_service = SlurmService(ssh_service=ssh_service)
        job_ids: list[SlurmJob] = await slurm_service.get_job_status_squeue(job_ids=[slurmjobid])
        if len(job_ids) == 0:
            job_ids = await slurm_service.get_job_status_sacct(job_ids=[slurmjobid])
            if len(job_ids) == 0:
                logger.warning(f"No job found with ID {slurmjobid} in both squeue and sacct.")
                return None
        if len(job_ids) == 1:
            return job_ids[0]
        else:
            raise RuntimeError(f"Multiple jobs found with ID {slurmjobid}: {job_ids}")

    @override
    async def close(self) -> None:
        pass
