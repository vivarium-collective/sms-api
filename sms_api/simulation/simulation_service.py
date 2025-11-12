import datetime
import json
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
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import Settings, get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import (
    VECOLI_REPO_NAME,
    get_apptainer_image_file,
    get_experiment_dir,
    get_experiment_path,
    get_parca_dataset_dir,
    get_parca_dataset_dirname,
    get_slurm_log_file,
    get_slurm_submit_file,
    get_slurmjob_name,
    get_vEcoli_repo_dir,
)
from sms_api.simulation.models import (
    EcoliSimulation,
    ParcaDataset,
    SimulationConfig,
    SimulationConfiguration,
    SimulatorVersion,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_SIMULATION_CPUS = 5


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
        self, ecoli_simulation: EcoliSimulation, database_service: DatabaseService, correlation_id: str
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

    @abstractmethod
    async def submit_experiment_job(
        self, config: SimulationConfig, simulation_name: str, simulator_hash: str, logger: logging.Logger
    ) -> tuple[str, int]:
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
        with open(Path(assets_dir) / "simulation" / "model" / "latest_commit.txt", "w") as f:
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
            known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
        )

        software_version_path = settings.hpc_repo_base_path / git_commit_hash
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
            known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
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
                nodelist_clause = f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 2
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    #SBATCH --qos={settings.slurm_qos}
                    #SBATCH --output={slurm_log_file}
                    {nodelist_clause}

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
            known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
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
                nodelist_clause = f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 3
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    #SBATCH --qos={settings.slurm_qos}
                    #SBATCH --output={slurm_log_file}
                    {nodelist_clause}

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
        self, ecoli_simulation: EcoliSimulation, database_service: DatabaseService, correlation_id: str
    ) -> int:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
            known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
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
                nodelist_clause = f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 2
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    #SBATCH --qos={settings.slurm_qos}
                    #SBATCH --output={slurm_log_file}
                    {nodelist_clause}

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
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def submit_experiment_job(
        self, config: SimulationConfig, simulation_name: str, simulator_hash: str, logger: logging.Logger
    ) -> tuple[str, int]:
        """Used by the /ecoli router"""

        async def _dispatch(
            config: SimulationConfig, simulation_name: str, simulator_hash: str, logger: logging.Logger
        ) -> tuple[str, int]:
            experiment_id = config.experiment_id
            slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)
            slurm_log_file = get_settings().slurm_base_path / "prod" / "htclogs" / f"{slurmjob_name}.out"

            slurm_script = _slurm_script(
                slurm_log_file=slurm_log_file,
                slurm_job_name=slurmjob_name,
                latest_hash=simulator_hash,
                config=config,
                simulation_name=simulation_name,
            )

            slurmjob_id = await _submit_script(
                config=config,
                script_content=slurm_script,
                slurm_job_name=slurmjob_name,
            )

            return slurmjob_name, slurmjob_id

        def _slurm_script(
            slurm_log_file: HPCFilePath,
            slurm_job_name: str,
            latest_hash: str,
            config: SimulationConfig,
            simulation_name: str,
        ) -> str:
            remote_workspace_dir = get_settings().slurm_base_path / "workspace"
            vecoli_dir = remote_workspace_dir / "vEcoli"
            # config_dir = vecoli_dir / "configs"
            # conf = config.model_dump_json() or "{}"
            nodelist_clause = f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""

            return dedent(f"""\
                #!/bin/bash
                #SBATCH --job-name={slurm_job_name}
                #SBATCH --time=30:00
                #SBATCH --cpus-per-task {MAX_SIMULATION_CPUS}
                #SBATCH --mem=8GB
                #SBATCH --partition={get_settings().slurm_partition}
                #SBATCH --qos={get_settings().slurm_qos}
                #SBATCH --output={slurm_log_file!s}
                {nodelist_clause}

                set -e

                ### set up java and nextflow
                local_bin=$HOME/.local/bin
                export JAVA_HOME=$local_bin/java-22
                export PATH=$JAVA_HOME/bin:$local_bin:$PATH

                ### configure working dir and binds
                vecoli_dir={vecoli_dir!s}
                latest_hash={latest_hash}

                tmp_config=$(mktemp)
                echo '{json.dumps(config.model_dump())}' > \"$tmp_config\"

                cd $vecoli_dir

                ### binds
                binds="-B $HOME/workspace/vEcoli:/vEcoli"
                binds+=" -B $HOME/workspace/api_outputs:/out"
                binds+=" -B $JAVA_HOME:$JAVA_HOME"
                binds+=" -B $HOME/.local/bin:$HOME/.local/bin"

                image=$HOME/workspace/images/vecoli-$latest_hash.sif
                vecoli_image_root=/vEcoli

                singularity run $binds $image bash -c "
                    export JAVA_HOME=$HOME/.local/bin/java-22
                    export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
                    uv run --env-file /vEcoli/.env /vEcoli/runscripts/workflow.py --config \"$tmp_config\"
                "
            """)

        async def _submit_script(
            config: SimulationConfig,
            script_content: str,
            slurm_job_name: str,
        ) -> int:
            ssh_service = get_ssh_service()
            slurm_service = SlurmService(ssh_service=ssh_service)

            slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
            with tempfile.TemporaryDirectory() as tmpdir:
                local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
                with open(local_submit_file, "w") as f:
                    f.write(script_content)

                # base_path = Path(env.slurm_base_path)
                # remote_workspace_dir = base_path / "workspace"
                # vecoli_dir = remote_workspace_dir / "vEcoli"
                # config_dir = vecoli_dir / "configs"

                slurm_jobid = await slurm_service.submit_job(
                    local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
                )
                return slurm_jobid

        return await _dispatch(config, simulation_name, simulator_hash, logger)

    @override
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
            known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
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


def simulation_slurm_script(
    config_id: str,
    slurm_job_name: str,
    experiment_id: str,
    settings: Settings | None = None,
    logger: logging.Logger | None = None,
    config: SimulationConfiguration | None = None,
) -> str:
    env = settings or get_settings()
    base_path = env.slurm_base_path
    remote_workspace_dir = base_path / "workspace"
    vecoli_dir = remote_workspace_dir / "vEcoli"
    slurm_log_file = base_path / "prod" / "htclogs" / f"{experiment_id}.out"
    experiment_outdir = HPCFilePath(remote_path=Path(f"/home/FCAM/svc_vivarium/workspace/api_outputs/{config_id}"))

    config_dir = vecoli_dir / "configs"
    latest_hash = "079c43c"

    conf = config.model_dump_json() if config else ""
    experiment_id = config.experiment_id if config is not None else experiment_id
    nodelist_clause = f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""

    return dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={slurm_job_name}
        #SBATCH --time=30:00
        #SBATCH --cpus-per-task 8
        #SBATCH --mem=8GB
        #SBATCH --partition={env.slurm_partition}
        #SBATCH --qos={env.slurm_qos}
        #SBATCH --output={slurm_log_file!s}
        {nodelist_clause}

        set -e

        ### set up java and nextflow
        local_bin=$HOME/.local/bin
        export JAVA_HOME=$local_bin/java-22
        export PATH=$JAVA_HOME/bin:$local_bin:$PATH
        # export NEXTFLOW=$local_bin/nextflow
        # export PATH=$JAVA_HOME/bin:$PATH:$(dirname "$NEXTFLOW")

        if [ '{conf}' != '' ]; then
            uv run python $HOME/workspace/scripts/write_uploaded_config.py --config '{conf}'
            cd $HOME/workspace/vEcoli
        else
            ### create request-specific config .json
            cd $HOME/workspace/vEcoli
            expid={experiment_id}
            config_id={config_id}
            config_dir={config_dir!s}
            experiment_config=$config_dir/$expid.json
            [ -f "$config_dir/$config_id.json" ] \
            && jq --arg expid "$expid" '.experiment_id = $expid' \
            "$config_dir/$config_id.json" > "$config_dir/$expid.json"
        fi

        ### logging to confirm installations/paths
        echo "----> START({datetime.datetime.now()}) ---->"
        echo "                                            "
        echo "===== Environment Variables ====="
        env | grep -E 'JAVA_HOME|PATH|NEXTFLOW'

        echo "=== Checking Java and Nextflow ==="
        jv=$(which java)
        nf=$(which nextflow)
        echo ">> Java path: $jv"
        echo ">> Nextflow path: $nf"
        echo ">> UV Installation: $(which uv)"
        echo ">> UV Python: $(uv run which python)"
        echo "$jv" > {remote_workspace_dir!s}/test-java.txt
        echo "$nf" > {remote_workspace_dir!s}/test-nextflow.txt
        echo "|<----------------- END <-------------------"
        echo "                                            "

        ### Check if the experiment dir exists, remove if so:
        if [ -d {experiment_outdir} ]; then rm -rf {experiment_outdir}; fi

        ### configure working dir and binds
        vecoli_dir={vecoli_dir!s}
        latest_hash={latest_hash}
        # cd $vecoli_dir

        ### bind vecoli and outputs dest dir
        binds="-B $HOME/workspace/vEcoli:/vEcoli"
        binds+=" -B $HOME/workspace/outputs:/out"

        ### bind java and nextflow
        binds+=" -B $JAVA_HOME:$JAVA_HOME"
        binds+=" -B $HOME/.local/bin:$HOME/.local/bin"

        # image="/home/FCAM/svc_vivarium/prod/images/vecoli-$latest_hash.sif"
        image=$HOME/workspace/images/vecoli-$latest_hash.sif
        vecoli_image_root=/vEcoli

        # singularity run $binds $image bash -c '
        #     export JAVA_HOME=$HOME/.local/bin/java-22
        #     export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
        #     uv run --env-file /vEcoli/.env /vEcoli/runscripts/workflow.py --config /vEcoli/configs/{config_id}.json
        # '

        ### remove unique sim config on exit, regardless of job outcome
        [ -f {config_dir!s}/{experiment_id}.json ] && trap 'rm -f {config_dir!s}/{experiment_id}.json' EXIT

        ### run bound singularity
        singularity run $binds $image bash -c "
            export JAVA_HOME=$HOME/.local/bin/java-22
            export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
            uv run --env-file /vEcoli/.env /vEcoli/runscripts/workflow.py --config /vEcoli/configs/{experiment_id}.json
        "
    """)


async def submit_slurm_script(
    script_content: str, slurm_job_name: str, env: Settings | None = None, ssh: SSHService | None = None
) -> int:
    settings = env or get_settings()
    ssh_service = ssh or SSHService(
        hostname=settings.slurm_submit_host,
        username=settings.slurm_submit_user,
        key_path=Path(settings.slurm_submit_key_path),
        known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
    )
    slurm_service = SlurmService(ssh_service=ssh_service)

    slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
    with tempfile.TemporaryDirectory() as tmpdir:
        local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
        with open(local_submit_file, "w") as f:
            f.write(script_content)

        slurm_jobid = await slurm_service.submit_job(
            local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
        )
        return slurm_jobid


def log(msg: str, logger: logging.Logger | None = None) -> None:
    logfunc = logger.info if logger else print
    return logfunc(msg)


async def submit_vecoli_job(
    config_id: str,
    simulator_hash: str,
    env: Settings,
    experiment_id: str,
    ssh: SSHService | None = None,
    logger: logging.Logger | None = None,
    config: SimulationConfiguration | None = None,
) -> int:
    # experiment_id = expid or create_experiment_id(config_id=config_id, simulator_hash=simulator_hash)
    experiment_dir = get_experiment_dir(experiment_id=experiment_id)
    experiment_path_parent = experiment_dir.parent
    experiment_id_dir = experiment_dir.name
    slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)
    # slurmjob_name = "dev"

    script = simulation_slurm_script(
        config_id=config_id,
        slurm_job_name=slurmjob_name,
        experiment_id=experiment_id,
        settings=env,
        logger=logger,
        config=config,
    )

    msg = dedent(f"""\
        Submitting with the following params:
        ====================================
        >> experimentid: {experiment_id}
        >> experimentidDir: {experiment_id_dir}
        >> experiment_dir: {experiment_dir}
        >> experiment_path_parent: {experiment_path_parent}
        >> slurmjobName: {slurmjob_name}
        >> slurmscript:\n{script}
        ====================================
    """)
    log(msg, logger)
    log("", logger)

    slurmjob_id = await submit_slurm_script(script_content=script, slurm_job_name=slurmjob_name, env=env, ssh=ssh)
    log(f"Submission Successful!!\nGenerated slurmjob ID: {slurmjob_id}", logger)

    return slurmjob_id
