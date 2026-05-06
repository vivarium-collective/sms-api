"""Compose simulation service — submits process-bigraph jobs to SLURM via sms-api SSH."""

import logging
import random
import string
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent

from typing_extensions import override

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.models import SSHTarget
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.compose.database_service import ComposeDatabaseService
from sms_api.compose.hpc_utils import (
    get_compose_correlation_id,
    get_compose_experiment_dir,
    get_compose_sim_input_path,
    get_compose_singularity_container_file,
    get_compose_singularity_def_file,
    get_compose_slurm_log_file,
    get_compose_slurm_submit_file,
)
from sms_api.compose.models import ComposeHpcRun, ComposeJobType, ComposeSimulation, ComposeSimulatorVersion
from sms_api.config import Settings, get_settings
from sms_api.dependencies import get_ssh_session_service

logger = logging.getLogger(__name__)


class ComposeSimulationService(ABC):
    @abstractmethod
    async def submit_simulation_job(self, simulation: ComposeSimulation, experiment_id: str) -> int:
        pass

    @abstractmethod
    async def build_container(
        self, simulator_version: ComposeSimulatorVersion, random_str: str, db_service: ComposeDatabaseService
    ) -> ComposeHpcRun:
        pass


class ComposeSimulationServiceHpc(ComposeSimulationService):
    env: Settings

    def __init__(self, env: Settings | None = None) -> None:
        self.env = env or get_settings()

    @override
    async def submit_simulation_job(self, simulation: ComposeSimulation, experiment_id: str) -> int:
        if simulation.sim_request.request_file_path is None:
            raise RuntimeError("Simulation request file path is not available.")

        slurm_job_name = experiment_id
        singularity_container = get_compose_singularity_container_file(
            singularity_hash=simulation.simulator_version.singularity_def_hash
        )
        experiment_path = get_compose_experiment_dir(experiment_id=slurm_job_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            script_content = dedent(f"""\
                #!/bin/bash
                #SBATCH --job-name={slurm_job_name}
                #SBATCH --time=30:00
                #SBATCH --cpus-per-task {"1" if simulation.sim_request.is_batch else "2"}
                #SBATCH --mem={"1GB" if simulation.sim_request.is_batch else "8GB"}
                #SBATCH --partition={self.env.slurm_partition}
                #SBATCH --output={get_compose_slurm_log_file(slurm_job_name=slurm_job_name)}

                set -e

                mkdir {experiment_path}/output
                echo "Simulation {slurm_job_name} running."
                singularity run \\
                    --compat \\
                    --bind {experiment_path}:/experiment \\
                    {singularity_container} \\
                    /experiment/{slurm_job_name}.{simulation.sim_request.simulation_file_type.get_files_suffix()} \\
                    -o "{self.env.compose_containers_output_dir}" \\
                    -n {simulation.sim_request.end_time_point}

                pushd {experiment_path}
                cd output
                zip -r ../results.zip ./*
                cd ..
                rm -r output
                popd
                echo "Simulation run completed. data saved to {experiment_path!s}."
                """)
            local_submit_file.write_text(script_content)

            async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
                await ssh.run_command(f"mkdir -p {experiment_path}")
                # Upload the simulation input file (OMEX/PBG/SBML)
                remote_input = HPCFilePath(remote_path=get_compose_sim_input_path(experiment_id=slurm_job_name))
                await ssh.scp_upload(local_file=simulation.sim_request.request_file_path, remote_path=remote_input)
                slurm_service = SlurmService()
                remote_sbatch = HPCFilePath(remote_path=get_compose_slurm_submit_file(slurm_job_name=slurm_job_name))
                slurm_jobid = await slurm_service.submit_job(
                    ssh,
                    local_sbatch_file=local_submit_file,
                    remote_sbatch_file=remote_sbatch,
                )
                return slurm_jobid

    @override
    async def build_container(
        self, simulator_version: ComposeSimulatorVersion, random_str: str, db_service: ComposeDatabaseService
    ) -> ComposeHpcRun:
        rand_string = "".join(random.choices(string.hexdigits, k=5))
        slurm_job_name = f"singularity_build_{simulator_version.singularity_def_hash[:5]}_{rand_string}"
        singularity_container = get_compose_singularity_container_file(
            singularity_hash=simulator_version.singularity_def_hash
        )
        singularity_def_file = get_compose_singularity_def_file(singularity_hash=simulator_version.singularity_def_hash)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_singularity_file = Path(tmpdir) / "singularity.def"
            local_singularity_file.write_text(simulator_version.singularity_def.representation)

            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            script_content = dedent(f"""\
                #!/bin/bash
                #SBATCH --job-name={slurm_job_name}
                #SBATCH --time=30:00
                #SBATCH --cpus-per-task 1
                #SBATCH --mem=4GB
                #SBATCH --partition={self.env.slurm_partition}
                #SBATCH --output={get_compose_slurm_log_file(slurm_job_name=slurm_job_name)}

                set -e
                echo "Starting build for container {singularity_container}"
                pushd /tmp
                mv {singularity_def_file} /tmp/{singularity_def_file.name}
                singularity build --fakeroot {singularity_container.name} {singularity_def_file.name}
                mv {singularity_container.name} {singularity_container}
                mv {singularity_def_file.name} {singularity_def_file}
                popd
                echo "Finished building container."
                """)
            local_submit_file.write_text(script_content)

            async with get_ssh_session_service(SSHTarget.SLURM).session() as ssh:
                slurm_service = SlurmService()
                remote_def = HPCFilePath(remote_path=singularity_def_file)
                await ssh.scp_upload(local_file=local_singularity_file, remote_path=remote_def)
                remote_sbatch = HPCFilePath(remote_path=get_compose_slurm_submit_file(slurm_job_name=slurm_job_name))
                slurm_jobid = await slurm_service.submit_job(
                    ssh,
                    local_sbatch_file=local_submit_file,
                    remote_sbatch_file=remote_sbatch,
                )

            hpc_run = await db_service.get_hpc_db().insert_hpcrun(
                slurmjobid=slurm_jobid,
                job_type=ComposeJobType.BUILD_CONTAINER,
                ref_id=simulator_version.database_id,
                correlation_id=get_compose_correlation_id(
                    random_string=random_str, job_type=ComposeJobType.BUILD_CONTAINER
                ),
            )
            return hpc_run
