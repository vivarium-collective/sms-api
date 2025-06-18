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
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.models import EcoliSimulationRequest, ParcaDataset, SimulatorVersion

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SimulationService(ABC):
    @abstractmethod
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        pass

    @abstractmethod
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        pass

    @abstractmethod
    async def submit_parca_job(self, parca_dataset: ParcaDataset) -> int:
        pass

    @abstractmethod
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        pass

    @abstractmethod
    async def clone_repository_if_needed(
        self,
        git_commit_hash: str,  # first 7 characters of the commit hash are used for the directory name
        git_repo_url: str = "https://github.com/CovertLab/vEcoli",
        git_branch: str = "master",
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
    @override
    async def clone_repository_if_needed(
        self,
        git_commit_hash: str,  # first 7 characters of the commit hash are used for the directory name
        git_repo_url: str = "https://github.com/CovertLab/vEcoli",
        git_branch: str = "master",
    ) -> None:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        return_code, stdout, stderr = await ssh_service.run_command(f"git ls-remote -h {git_repo_url} {git_branch}")
        if return_code != 0:
            raise RuntimeError(f"Failed to list git commits for repository: {stderr.strip()}")
        latest_commit_hash = stdout.strip("\n")[:7]
        if latest_commit_hash != git_commit_hash:
            raise ValueError(
                f"Provided git commit hash {git_commit_hash} does not match "
                f"the latest commit hash {latest_commit_hash} for branch {git_branch} of repository {git_repo_url}"
            )

        software_version_path = Path(settings.hpc_repo_base_path) / git_commit_hash
        test_cmd = f"test -d {software_version_path!s}"
        dir_cmd = f"mkdir -p {software_version_path!s} && cd {software_version_path!s}"
        clone_cmd = f"git clone --depth 1 --branch {git_branch} {git_repo_url}"
        # skip if directory exists, otherwise create it and clone the repo
        command = f"{test_cmd} || ({dir_cmd} && {clone_cmd})"
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

        slurm_log_remote_path = Path(settings.slurm_log_base_path)
        slurm_log_file = slurm_log_remote_path / f"{slurm_job_name}.out"
        slurm_submit_file = slurm_log_remote_path / f"{slurm_job_name}.sbatch"

        version_base_remote_path = Path(settings.hpc_repo_base_path) / simulator_version.git_commit_hash
        remote_build_script_relative_path = Path("runscripts") / "container" / "build-image.sh"
        remote_vEcoli_path = version_base_remote_path / "vEcoli"

        hpc_image_remote_path = Path(settings.hpc_image_base_path)
        apptainer_image_path = hpc_image_remote_path / f"vecoli-{simulator_version.git_commit_hash}.sif"

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

                    echo "Building vEcoli image for commit {simulator_version.git_commit_hash} on $(hostname) ..."
                    env
                    mkdir -p {hpc_image_remote_path!s}

                    # if the image already exists, skip the build
                    if [ -f {apptainer_image_path!s} ]; then
                        echo "Image {apptainer_image_path!s} already exists. Skipping build."
                        exit 0
                    fi

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

        slurm_log_remote_path = Path(settings.slurm_log_base_path)
        slurm_log_file = slurm_log_remote_path / f"{slurm_job_name}.out"
        slurm_submit_file = slurm_log_remote_path / f"{slurm_job_name}.sbatch"

        parca_remote_path = Path(settings.hpc_parca_base_path) / f"id_{parca_dataset.database_id}"
        remote_vEcoli_repo_path = Path(settings.hpc_repo_base_path) / simulator_version.git_commit_hash / "vEcoli"

        hpc_image_remote_path = Path(settings.hpc_image_base_path)
        apptainer_image_path = hpc_image_remote_path / f"vecoli-{simulator_version.git_commit_hash}.sif"

        # apptainer run \
        #     --bind /home/FCAM/svc_vivarium/test/repos/8ed6a30/vEcoli:/vEcoli \
        #     --bind /home/FCAM/svc_vivarium/test:/parca_out \
        #     /home/FCAM/svc_vivarium/test/images/vecoli-8ed6a30.sif \
        # uv run \
        # --env-file /vEcoli/.env \
        # /vEcoli/runscripts/parca.py \
        # --config /vEcoli/ecoli/composites/ecoli_configs/run_parca.json \
        # -c 3 \
        # -o /parca_out/parca_1

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
                         --config /vEcoli/ecoli/composites/ecoli_configs/run_parca.json -c 3 -o /parca_out

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
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        return -1

    @override
    async def get_slurm_job_status(self, slurmjobid: int) -> SlurmJob | None:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        slurm_service = SlurmService(ssh_service=ssh_service)
        job_ids: list[SlurmJob] = await slurm_service.get_job_status(job_id=slurmjobid)
        if len(job_ids) == 0:
            return None
        elif len(job_ids) == 1:
            return job_ids[0]
        else:
            raise RuntimeError(f"Multiple jobs found with ID {slurmjobid}: {job_ids}")

    @override
    async def close(self) -> None:
        pass
