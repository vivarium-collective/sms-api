import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from textwrap import dedent

from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.models import EcoliSimulationRequest, SimulatorVersion

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SimulationService(ABC):
    @abstractmethod
    async def submit_parca_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        pass

    @abstractmethod
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        pass

    @abstractmethod
    async def submit_build_image_job(self, simulator_version: SimulatorVersion) -> int:
        pass

    @abstractmethod
    async def get_slurm_job_status(self, slurmjobid: str) -> SlurmJob | None:
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
    async def submit_parca_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        settings = get_settings()
        ssh_service = SSHService(
            hostname=settings.slurm_submit_host,
            username=settings.slurm_submit_user,
            key_path=Path(settings.slurm_submit_key_path),
        )
        slurm_service = SlurmService(ssh_service=ssh_service)

        # create Parca job submission script
        parca_submission_script = """
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            local_sbatch_file_path = tmpdir_path / "parca_submission.sbatch"
            remote_sbatch_file_path = Path("parca_files") / "parca_submission.sbatch"

            # write the sbatch file
            with open(local_sbatch_file_path, "w") as sbatch_file:
                sbatch_file.write(parca_submission_script)

            # submit the job to Slurm
            slurmjobid = await slurm_service.submit_job(
                local_sbatch_file=local_sbatch_file_path, remote_sbatch_file=remote_sbatch_file_path
            )

            return slurmjobid

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

        slurm_job_name = f"build-image-{simulator_version.git_commit_hash}"

        slurm_log_remote_path = Path(settings.slurm_log_base_path)
        slurm_log_file = slurm_log_remote_path / f"{slurm_job_name}.out"
        slurm_submit_file = slurm_log_remote_path / f"{slurm_job_name}.sbatch"

        version_base_remote_path = Path(settings.hpc_repo_base_path) / simulator_version.git_commit_hash
        remote_build_script_path = version_base_remote_path / "vEcoli" / "runscripts" / "container" / "build-image.sh"

        apptainer_image_path = slurm_log_remote_path / f"vecoli-{simulator_version.git_commit_hash}.sif"

        # build the submit script
        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                build_image_cmd = f"{remote_build_script_path!s} -i {apptainer_image_path!s} -a"
                script_content = dedent(f"""\
                    #!/bin/bash
                    #SBATCH --job-name={slurm_job_name}
                    #SBATCH --time=30:00
                    #SBATCH --cpus-per-task 2
                    #SBATCH --mem=8GB
                    #SBATCH --partition={settings.slurm_partition}
                    #SBATCH --wait
                    #SBATCH --output={slurm_log_file}
                    {build_image_cmd}
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
    async def get_slurm_job_status(self, slurmjobid: str) -> SlurmJob | None:
        return None

    @override
    async def close(self) -> None:
        pass
