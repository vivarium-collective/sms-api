import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.simulation.models import EcoliSimulationRequest

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
    async def get_slurm_job_status(self, slurmjobid: str) -> SlurmJob | None:
        pass

    @abstractmethod
    async def clone_repository_if_needed(
        self,
        git_commit_hash: str,
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
        git_commit_hash: str,
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
        latest_commit_hash = stdout.strip("\n").split()[0]
        if latest_commit_hash != git_commit_hash:
            raise ValueError(
                f"Provided git commit hash {git_commit_hash} does not match "
                f"the latest commit hash {latest_commit_hash} for branch {git_branch} of repository {git_repo_url}"
            )

        dir_cmd = (
            f"HASH_DIR=$(git ls-remote -h {git_repo_url} {git_branch} | cut -f 1) && mkdir -p $HASH_DIR && cd $HASH_DIR"
        )
        test_dir_cmd = f"test -d {git_commit_hash}"
        clone_cmd = f"git clone --depth 1 --branch {git_branch} {git_repo_url}"
        return_code, stdout, stderr = await ssh_service.run_command(f"{test_dir_cmd} || ({dir_cmd} && {clone_cmd})")
        if return_code != 0:
            raise RuntimeError(
                f"Failed to clone repo {git_repo_url} branch {git_branch} hash {git_commit_hash}: {stderr.strip()}"
            )

    @override
    async def submit_sim_job(self, simulation_run_id: EcoliSimulationRequest) -> int:
        return -1

    @override
    async def get_slurm_job_status(self, slurmjobid: str) -> SlurmJob | None:
        return None

    @override
    async def close(self) -> None:
        pass
