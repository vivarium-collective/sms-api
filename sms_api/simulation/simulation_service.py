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
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import Settings, get_settings
from sms_api.dependencies import get_ssh_session_service
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.hpc_utils import (
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
    ParcaDataset,
    Simulation,
    SimulationConfig,
    SimulatorVersion,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_SIMULATION_CPUS = 5


class SimulationService(ABC):
    @abstractmethod
    async def get_latest_commit_hash(
        self,
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
        self, ecoli_simulation: Simulation, database_service: DatabaseService, correlation_id: str
    ) -> int:
        pass

    @abstractmethod
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def submit_experiment_job(
        self, config: SimulationConfig, simulator_hash: str, logger: logging.Logger
    ) -> tuple[str, int]:
        pass


def capture_slurm_script(script: str, fp: str) -> None:
    with open(fp, "w") as f:
        f.write(script)


class SimulationServiceHpc(SimulationService):
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
        async with get_ssh_session_service().session() as ssh:
            return_code, stdout, stderr = await ssh.run_command(f"git ls-remote -h {git_repo_url} {git_branch}")
        if return_code != 0:
            raise RuntimeError(f"Failed to list git commits for repository: {stderr.strip()}")
        latest_commit_hash = stdout.strip("\n")[:7]
        assets_dir = get_settings().assets_dir
        with open(Path(assets_dir) / "simulation" / "model" / "latest_commit.txt", "w") as f:
            f.write(latest_commit_hash)

        self._latest_commit_hash = latest_commit_hash
        return latest_commit_hash

    @override
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        settings = get_settings()
        slurm_service = SlurmService()

        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        slurm_job_name = f"build-image-{simulator_version.git_commit_hash}-{random_suffix}"

        slurm_log_file = get_slurm_log_file(slurm_job_name=slurm_job_name)
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
        remote_vEcoli_path = get_vEcoli_repo_dir(simulator_version=simulator_version)
        apptainer_image_path = get_apptainer_image_file(simulator_version=simulator_version)

        # build the submit script
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                qos_clause = f"#SBATCH --qos={get_settings().slurm_qos}" if get_settings().slurm_qos else ""
                nodelist_clause = (
                    f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""
                )
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 3
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    {qos_clause}
                    #SBATCH --mail-type=ALL
                    {nodelist_clause}
                    #SBATCH -o {slurm_log_file!s}
                    #SBATCH -e {slurm_log_file!s}

                    set -eu
                    env

                    # Determine which container runtime to use (prefer apptainer over singularity)
                    if command -v apptainer &> /dev/null; then
                        CONTAINER_CMD="apptainer"
                        echo "Using apptainer for container build"
                    elif command -v singularity &> /dev/null; then
                        CONTAINER_CMD="singularity"
                        echo "Using singularity for container build"
                    else
                        echo "ERROR: Neither apptainer nor singularity found in PATH"
                        exit 1
                    fi

                    # Set Apptainer/Singularity cache directories with defaults if not already set
                    export APPTAINER_CACHEDIR=${{APPTAINER_CACHEDIR:-$HOME/.apptainer/cache}}
                    export APPTAINER_TMPDIR=${{APPTAINER_TMPDIR:-$HOME/.apptainer/tmp}}
                    mkdir -p $APPTAINER_CACHEDIR $APPTAINER_TMPDIR

                    # Step 1: Clone repository if needed
                    echo "=== Step 1: Cloning repository ==="
                    FINAL_REPO_PATH="{remote_vEcoli_path!s}"

                    if [ -d "$FINAL_REPO_PATH" ]; then
                        echo "Repository already exists at $FINAL_REPO_PATH"
                        # If repo already exists and image exists, skip everything
                        if [ -f {apptainer_image_path!s} ]; then
                            echo "Image {apptainer_image_path!s} already exists. Skipping build."
                            exit 0
                        fi
                        # Use existing repo for build
                        TMP_REPO_PATH="$FINAL_REPO_PATH"
                        MOVE_REPO=false
                    else
                        echo "Repository not found. Cloning to /tmp..."
                        # Clone to /tmp to avoid NFS issues during build
                        TMP_REPO_PATH="/tmp/slurm_job_${{SLURM_JOB_ID}}_vEcoli"
                        cd /tmp
                        git clone --branch {simulator_version.git_branch} \\
                                  --single-branch {simulator_version.git_repo_url} "$TMP_REPO_PATH"
                        cd "$TMP_REPO_PATH"
                        git checkout {simulator_version.git_commit_hash}
                        echo "Repository cloned successfully to $TMP_REPO_PATH"
                        MOVE_REPO=true
                        # Cleanup temp repo on exit (if we fail before moving)
                        trap "rm -rf '$TMP_REPO_PATH'" EXIT
                    fi

                    # Step 2: Build Apptainer image
                    echo "=== Step 2: Building Apptainer image ==="
                    mkdir -p {apptainer_image_path.parent!s}

                    echo "Building vEcoli image for commit {simulator_version.git_commit_hash} on $(hostname)..."
                    echo "Building from $TMP_REPO_PATH (local filesystem)"

                    cd "$TMP_REPO_PATH"

                    # Get git info
                    GIT_HASH=$(git rev-parse HEAD)
                    GIT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "detached")
                    TIMESTAMP=$(date '+%Y%m%d.%H%M%S')

                    # Create git diff
                    mkdir -p source-info
                    git diff HEAD > source-info/git_diff.txt

                    # Create repo.tar (respecting .dockerignore)
                    echo "Creating repo tarball..."
                    EXCLUDE_PATTERNS=$(mktemp)
                    if [ -f .dockerignore ]; then
                        grep -v "^#" .dockerignore | grep -v "^$" | grep -v "^!" | while read -r pattern; do
                            if [[ "$pattern" == /* ]]; then
                                echo ".${{pattern}}/*" >> "$EXCLUDE_PATTERNS"
                            elif [[ "$pattern" == */ ]]; then
                                echo "./${{pattern}}*" >> "$EXCLUDE_PATTERNS"
                            else
                                echo "./${{pattern}}" >> "$EXCLUDE_PATTERNS"
                                echo "./${{pattern}}/*" >> "$EXCLUDE_PATTERNS"
                            fi
                        done
                    fi

                    FIND_CMD="find . -type f"
                    while read -r pattern; do
                        FIND_CMD="$FIND_CMD ! -path \\"$pattern\\""
                    done < "$EXCLUDE_PATTERNS"

                    TEMP_FILE_LIST=$(mktemp)
                    eval "$FIND_CMD -print0" > "$TEMP_FILE_LIST"
                    tar -cf repo.tar --null -T "$TEMP_FILE_LIST"
                    rm -f "$EXCLUDE_PATTERNS" "$TEMP_FILE_LIST"
                    echo "Created repo.tar ($(du -sh repo.tar | awk '{{print $1}}'))"

                    # Process .env file for environment variables
                    DOT_ENV_VARS="    "
                    if [ -f .env ]; then
                        echo "Processing .env for Singularity environment..."
                        while IFS= read -r line || [ -n "$line" ]; do
                            if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
                                line=${{line#export }}
                                DOT_ENV_VARS+="export $line; "
                            fi
                        done < .env
                        echo "Found $(echo "$DOT_ENV_VARS" | grep -c 'export ') environment variables"
                    fi

                    # Build container image
                    echo "=== Building Container Image: {apptainer_image_path!s} ==="
                    echo "=== git hash $GIT_HASH, git branch $GIT_BRANCH ==="

                    if ! $CONTAINER_CMD build --fakeroot --force \\
                        --build-arg git_hash="$GIT_HASH" \\
                        --build-arg git_branch="$GIT_BRANCH" \\
                        --build-arg timestamp="$TIMESTAMP" \\
                        --build-arg dot_env_vars="$DOT_ENV_VARS" \\
                        {apptainer_image_path!s} runscripts/container/Singularity; then
                        echo "ERROR: Container build failed."
                        exit 1
                    fi
                    echo "Container build successful!"

                    # Cleanup temp files
                    rm -f source-info/git_diff.txt repo.tar

                    echo "Build completed. Image saved to {apptainer_image_path!s}."

                    # Step 3: Move repository to final location if needed
                    if [ "$MOVE_REPO" = true ]; then
                        echo "=== Step 3: Moving repository to final location ==="
                        mkdir -p "{remote_vEcoli_path.parent!s}"
                        mv "$TMP_REPO_PATH" "$FINAL_REPO_PATH"
                        echo "Repository moved to $FINAL_REPO_PATH"
                    fi
                    """)
                capture_slurm_script(script_content, "assets/build_image.sbatch")
                f.write(script_content)

            # submit the build script to slurm
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        settings = get_settings()
        slurm_service = SlurmService()
        simulator_version = parca_dataset.parca_dataset_request.simulator_version

        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
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
                qos_clause = f"#SBATCH --qos={get_settings().slurm_qos}" if get_settings().slurm_qos else ""
                nodelist_clause = (
                    f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""
                )
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 3
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    {qos_clause}
                    #SBATCH --mail-type=ALL
                    {nodelist_clause}
                    #SBATCH -o {slurm_log_file!s}
                    #SBATCH -e {slurm_log_file!s}

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
                capture_slurm_script(script_content, "assets/parca.sbatch")
                f.write(script_content)

            # submit the build script to slurm
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def submit_ecoli_simulation_job(
        self, ecoli_simulation: Simulation, database_service: DatabaseService, correlation_id: str
    ) -> int:
        settings = get_settings()
        if database_service is None:
            raise RuntimeError("DatabaseService is not available. Cannot submit Simulation job.")

        parca_dataset = await database_service.get_parca_dataset(parca_dataset_id=ecoli_simulation.parca_dataset_id)
        if parca_dataset is None:
            raise ValueError(f"ParcaDataset with ID {ecoli_simulation.parca_dataset_id} not found.")

        slurm_service = SlurmService()
        simulator_version = parca_dataset.parca_dataset_request.simulator_version

        random_suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        slurm_job_name = f"sim-{simulator_version.git_commit_hash}-{ecoli_simulation.database_id}-{random_suffix}"

        slurm_log_file = get_slurm_log_file(slurm_job_name=slurm_job_name)
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
        parca_dataset_path = get_parca_dataset_dir(parca_dataset=parca_dataset)
        parca_parent_path = parca_dataset_path.parent
        parca_dataset_dirname = get_parca_dataset_dirname(parca_dataset)
        experiment_path = get_experiment_path(ecoli_simulation=ecoli_simulation, simulator=simulator_version)
        experiment_path_parent = experiment_path.parent
        experiment_id = experiment_path.name
        hpc_sim_config_file = settings.hpc_sim_config_file
        remote_vEcoli_repo_path = get_vEcoli_repo_dir(simulator_version=simulator_version)
        apptainer_image_path = get_apptainer_image_file(simulator_version=simulator_version)

        simulator = await database_service.get_simulator(simulator_id=ecoli_simulation.simulator_id)

        # uv run --env-file .env ecoli/experiments/ecoli_master_sim.py \
        #             --generations 1 --emitter parquet --emitter_arg out_dir='out' \
        #             --experiment_id "parca_1" --daughter_outdir "out/parca_1" \
        #             --sim_data_path "out/parca_1/kb/simData.cPickle" ----fail_at_max_duration

        # build the submit script
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                qos_clause = f"#SBATCH --qos={get_settings().slurm_qos}" if get_settings().slurm_qos else ""
                nodelist_clause = (
                    f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""
                )
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 2
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    {qos_clause}
                    #SBATCH -o {slurm_log_file!s}
                    #SBATCH -e {slurm_log_file!s}
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

                    # create custom config file mapped to /out/configs/ directory
                    mkdir -p {experiment_path_parent!s}/configs

                    # Check if the config template file exists (newer repos with messaging)
                    config_template_file={remote_vEcoli_repo_path!s}/configs/{hpc_sim_config_file}
                    default_config_file={remote_vEcoli_repo_path!s}/configs/default.json

                    if [ -f "$config_template_file" ]; then
                        echo "Using config template: {hpc_sim_config_file} (with messaging support)"
                        config_file={experiment_path_parent!s}/configs/{hpc_sim_config_file}_{experiment_id}.json
                        cp "$config_template_file" "$config_file"
                        # Replace template variables for messaging
                        sed -i "s/CORRELATION_ID_REPLACE_ME/{correlation_id}/g" "$config_file"
                        sed -i "s/REDIS_HOST_REPLACE_ME/{get_settings().redis_external_host}/g" "$config_file"
                        sed -i "s/REDIS_PORT_REPLACE_ME/{get_settings().redis_external_port}/g" "$config_file"
                        sed -i "s/REDIS_CHANNEL_REPLACE_ME/{get_settings().redis_channel}/g" "$config_file"
                    elif [ -f "$default_config_file" ]; then
                        echo "Using default config: default.json (older repo without messaging)"
                        config_file={experiment_path_parent!s}/configs/default_{experiment_id}.json
                        # Copy default config without template replacements
                        cp "$default_config_file" "$config_file"
                    else
                        echo "ERROR: Neither {hpc_sim_config_file} nor default.json found in configs/"
                        exit 1
                    fi

                    git -C ./configs diff HEAD >> ./source-info/git_diff.txt

                    # Determine the config path inside the container (bind mount at /out/configs/)
                    config_filename=$(basename "$config_file")
                    container_config_path="/out/configs/$config_filename"

                    # singularity run $binds $image uv run \\
                    #      --env-file /vEcoli/.env /vEcoli/ecoli/experiments/ecoli_master_sim.py \\
                    #      --config "$container_config_path" \\
                    #      --generations 1 --emitter parquet --emitter_arg out_dir='/out' \\
                    #      --experiment_id {experiment_id} \\
                    #      --daughter_outdir "/out/{experiment_id}" \\
                    #      --sim_data_path "/parca/{parca_dataset_dirname}/kb/simData.cPickle" \\
                    #      --fail_at_max_duration
                    ### set up java and nextflow
                    local_bin=$HOME/.local/bin
                    export JAVA_HOME=$local_bin/java-22
                    export PATH=$JAVA_HOME/bin:$local_bin:$PATH
                    ### configure working dir and binds
                    vecoli_dir={get_settings().vecoli_config_dir.parent.parent!s}
                    latest_hash={simulator.git_commit_hash}
                    tmp_config=$(mktemp)
                    echo '{json.dumps(ecoli_simulation.config.model_dump())}' > \"$tmp_config\"
                    cd /home/FCAM/svc_vivarium/workspace/vEcoli
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

                    # if the experiment directory is empty after the run, fail the job
                    if [ ! "$(ls -A {experiment_path!s})" ]; then
                        echo "Simulation output directory {experiment_path!s} is empty. Job must have failed."
                        exit 1
                    fi

                    echo "Simulation run completed. data saved to {experiment_path!s}."
                    """)
                capture_slurm_script(script_content, "assets/simulation.sbatch")
                f.write(script_content)

            # submit the build script to slurm
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    @override
    async def submit_experiment_job(
        self, config: SimulationConfig, simulator_hash: str, logger: logging.Logger
    ) -> tuple[str, int]:
        """Used by the /ecoli router"""

        async def _dispatch(config: SimulationConfig, simulator_hash: str, logger: logging.Logger) -> tuple[str, int]:
            experiment_id = config.experiment_id
            slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)
            slurm_log_file = get_settings().slurm_base_path / "prod" / "htclogs" / f"{slurmjob_name}.out"

            slurm_script = _slurm_script(
                slurm_log_file=slurm_log_file, slurm_job_name=slurmjob_name, latest_hash=simulator_hash, config=config
            )
            capture_slurm_script(slurm_script, "assets/simulation.sbatch")

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
        ) -> str:
            remote_workspace_dir = get_settings().slurm_base_path / "workspace"
            vecoli_dir = remote_workspace_dir / "vEcoli"
            env = get_settings()

            qos_clause = f"#SBATCH --qos={env.slurm_qos}" if env.slurm_qos else ""
            nodelist_clause = f"#SBATCH --nodelist={env.slurm_node_list}" if env.slurm_node_list else ""

            return dedent(f"""\
                #!/bin/bash
                #SBATCH --job-name={slurm_job_name}
                #SBATCH --time=1:00:00
                #SBATCH --cpus-per-task 3
                #SBATCH --mem=8GB
                #SBATCH --partition={env.slurm_partition}
                {qos_clause}
                #SBATCH --mail-type=ALL
                {nodelist_clause}
                #SBATCH -o {slurm_log_file!s}
                #SBATCH -e {slurm_log_file!s}

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
            slurm_service = SlurmService()

            slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)
            with tempfile.TemporaryDirectory() as tmpdir:
                local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
                with open(local_submit_file, "w") as f:
                    f.write(script_content)

                slurm_jobid = await slurm_service.submit_job(
                    local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
                )
                return slurm_jobid

        return await _dispatch(config, simulator_hash=simulator_hash, logger=logger)

    @override
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        slurm_service = SlurmService()
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
    config: SimulationConfig | None = None,
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
    qos_clause = f"#SBATCH --qos={get_settings().slurm_qos}" if get_settings().slurm_qos else ""
    nodelist_clause = f"#SBATCH --nodelist={get_settings().slurm_node_list}" if get_settings().slurm_node_list else ""

    return dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={slurm_job_name}
        #SBATCH --time=30:00
        #SBATCH --cpus-per-task 8
        #SBATCH --mem=8GB
        #SBATCH --partition={env.slurm_partition}
        {qos_clause}
        #SBATCH -o {slurm_log_file!s}
        #SBATCH -e {slurm_log_file!s}
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
    script_content: str,
    slurm_job_name: str,
) -> int:
    slurm_service = SlurmService()

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
    experiment_id: str,
    logger: logging.Logger | None = None,
    config: SimulationConfig | None = None,
) -> int:
    experiment_dir = get_experiment_dir(experiment_id=experiment_id)
    experiment_path_parent = experiment_dir.parent
    experiment_id_dir = experiment_dir.name
    slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)

    script = simulation_slurm_script(
        config_id=config_id,
        slurm_job_name=slurmjob_name,
        experiment_id=experiment_id,
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

    slurmjob_id = await submit_slurm_script(script_content=script, slurm_job_name=slurmjob_name)
    log(f"Submission Successful!!\nGenerated slurmjob ID: {slurmjob_id}", logger)

    return slurmjob_id
