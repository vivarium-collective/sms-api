import asyncio
import dataclasses
import json
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest

from sms_api.common.hpc.models import SlurmJob
from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHSessionService, SSHSession
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import get_settings
from sms_api.dependencies import get_ssh_session_service


class NextflowJobError(Exception):
    pass


@dataclasses.dataclass
class NextflowJobSubmission:
    job_id: int
    remote_output_file: HPCFilePath
    remote_error_file: HPCFilePath
    simulation_output_dir: HPCFilePath


class NextflowServiceSlurm:
    async def submit_simulation_job(
            self,
            slurm_service: SlurmService,
            ssh: SSHSession,
            sms_ccam_main_real_nf: str,
            sms_ccam_workflow_config_real: str,
            nextflow_config_sms_ccam_real: str,
            slurm_template_nextflow_sms_ccam_real: str,
    ) -> NextflowJobSubmission:
        """
        Integration test for real SMS CCAM simulation using SLURM executor.

        This test:
        - Runs an actual vEcoli simulation (not stub mode)
        - Uses existing parca dataset to skip ParCa step
        - Uses Singularity container with vEcoli image
        - Produces parquet output files
        - Uses hpc_sim_base_path for output directory

        Note: This test takes longer than the stub test (~5-30 minutes depending
        on simulation parameters). It's meant to verify the full simulation
        pipeline works correctly.
        """
        settings = get_settings()
        job_uuid = uuid.uuid4().hex[:8]
        experiment_id = f"integration_test_{job_uuid}"

        # Use hpc_sim_base_path for output
        output_base_path = settings.hpc_sim_base_path
        remote_base_path = settings.slurm_log_base_path

        # Paths for existing resources
        sim_data_path = "/projects/SMS/sms_api/alex/parca/parca_8f119dd_id_1/kb/simData.cPickle"
        container_image = "/projects/SMS/sms_api/alex/images/vecoli-8f119dd.sif"

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_dir = Path(tmpdir)
            file_prefix = f"sms_ccam_real_{job_uuid}"

            # Output directory for simulation results
            test_output_dir = HPCFilePath(remote_path=Path(str(output_base_path.remote_path) + f"/{experiment_id}"))

            # Write main.nf to local temp file
            local_nf_script = tmp_dir / f"{file_prefix}.nf"
            with open(local_nf_script, "w") as f:
                f.write(sms_ccam_main_real_nf)

            # Update workflow config with actual paths
            workflow_config_content = (
                sms_ccam_workflow_config_real.replace("PUBLISH_DIR_PLACEHOLDER", str(test_output_dir.remote_path))
            )

            # Write workflow_config.json to local temp file
            local_workflow_config = tmp_dir / "workflow_config.json"
            with open(local_workflow_config, "w") as f:
                f.write(workflow_config_content)

            # Dev: write out fully parsed to artifacts
            with open("assets/artifacts/workflow_config_real.json", "w") as fp:
                json.dump(json.loads(workflow_config_content), fp, indent=3)

            # Calculate remote paths (wrap in HPCFilePath for scp_upload)
            remote_nf_script = HPCFilePath(remote_path=remote_base_path.remote_path / local_nf_script.name)
            remote_workflow_config = HPCFilePath(remote_path=test_output_dir.remote_path / "workflow_config.json")
            remote_nf_config_path = HPCFilePath(remote_path=remote_base_path.remote_path / f"{file_prefix}.config")
            remote_output_file = remote_base_path.remote_path / f"{file_prefix}.out"
            remote_error_file = remote_base_path.remote_path / f"{file_prefix}.err"
            remote_report_file = remote_base_path.remote_path / f"{file_prefix}.report.html"
            remote_trace_file = remote_base_path.remote_path / f"{file_prefix}.trace.txt"
            remote_events_file = remote_base_path.remote_path / f"{file_prefix}.events.ndjson"
            remote_work_dir = remote_base_path.remote_path / f"{file_prefix}_work"

            # Update nextflow config with actual paths
            config_content = (
                nextflow_config_sms_ccam_real.replace("WORK_DIR_PLACEHOLDER", str(remote_work_dir))
                .replace("WORKFLOW_CONFIG_PATH", str(remote_workflow_config.remote_path))
                .replace("PUBLISH_DIR_PLACEHOLDER", str(test_output_dir.remote_path))
                .replace("EXPERIMENT_ID_PLACEHOLDER", experiment_id)
                .replace("SIM_DATA_PATH_PLACEHOLDER", sim_data_path)
                .replace("CONTAINER_IMAGE_PLACEHOLDER", container_image)
            )

            # Write nextflow config to local temp file
            local_nf_config = tmp_dir / f"{file_prefix}.config"
            with open(local_nf_config, "w") as f:
                f.write(config_content)

            # Build sbatch content with placeholders replaced
            sbatch_content = (
                slurm_template_nextflow_sms_ccam_real.replace("NEXTFLOW_SCRIPT_PATH", str(remote_nf_script.remote_path))
                .replace("REMOTE_LOG_OUTPUT_FILE", str(remote_output_file))
                .replace("REMOTE_LOG_ERROR_FILE", str(remote_error_file))
                .replace("REMOTE_REPORT_FILE", str(remote_report_file))
                .replace("REMOTE_TRACE_FILE", str(remote_trace_file))
                .replace("REMOTE_EVENTS_FILE", str(remote_events_file))
                .replace("NEXTFLOW_CONFIG_PATH", str(remote_nf_config_path.remote_path))
            )

            # Use real profile instead of stub mode
            sbatch_content = sbatch_content.replace(
                'nextflow run "$NF_SCRIPT"',
                'nextflow run "$NF_SCRIPT" -profile ccam_real',
            )

            # Write sbatch script to local temp file
            local_sbatch_file = tmp_dir / f"{file_prefix}.sbatch"
            with open(local_sbatch_file, "w") as f:
                f.write(sbatch_content)

            remote_sbatch_file = HPCFilePath(remote_path=remote_base_path.remote_path / local_sbatch_file.name)

            # Create remote output directory for workflow_config.json
            await ssh.run_command(f"mkdir -p {test_output_dir.remote_path}")
            # Upload all files to remote
            await ssh.scp_upload(local_nf_script, remote_nf_script)
            await ssh.scp_upload(local_nf_config, remote_nf_config_path)
            await ssh.scp_upload(local_workflow_config, remote_workflow_config)
            # Submit the Slurm job
            job_id: int = await slurm_service.submit_job(
                ssh, local_sbatch_file=local_sbatch_file, remote_sbatch_file=remote_sbatch_file
            )
            if job_id <= 0:
                raise RuntimeError(f"Failed to get valid job ID")

            submission = NextflowJobSubmission(
                job_id=job_id,
                remote_output_file=HPCFilePath(remote_path=remote_output_file),
                remote_error_file=HPCFilePath(remote_path=remote_error_file),
                simulation_output_dir=test_output_dir
            )

            # return job_id, HPCFilePath(remote_path=remote_output_file), HPCFilePath(remote_path=(remote_error_file))
            return submission

    async def poll_simulation_job(
            self,
            job_id: int,
            slurm_service: SlurmService,
            ssh: SSHSession,
            remote_output_file: HPCFilePath,
            remote_error_file: HPCFilePath,
            max_wait_seconds: int = 7200,
            poll_interval_seconds: int = 30,
            elapsed_seconds: int = 0,
    ) -> SlurmJob:
        # Poll for job completion (longer timeout for real simulation)
        final_job: SlurmJob | None = None

        while elapsed_seconds < max_wait_seconds:
            # Check squeue first (for running/pending jobs)
            jobs: list[SlurmJob] = await slurm_service.get_job_status_squeue(ssh, job_ids=[job_id])
            if len(jobs) > 0 and jobs[0].job_state.upper() in ["PENDING", "RUNNING", "CONFIGURING"]:
                await asyncio.sleep(poll_interval_seconds)
                elapsed_seconds += poll_interval_seconds
                continue

            # Check sacct for completed jobs
            jobs = await slurm_service.get_job_status_sacct(ssh, job_ids=[job_id])
            if len(jobs) > 0:
                final_job = jobs[0]
                if final_job.is_done():
                    break

            await asyncio.sleep(poll_interval_seconds)
            elapsed_seconds += poll_interval_seconds

        # Assertions
        if final_job is None:
            raise NextflowJobError(
                f"Real simulation job {job_id} not found after {max_wait_seconds} seconds"
            )

        if final_job.name != "nextflow_sms_ccam_real": raise NextflowJobError(f"Unexpected job name: {final_job.name}")
        if final_job.job_state.upper() != "COMPLETED": raise NextflowJobError((
            f"Real simulation failed with state: {final_job.job_state}, exit code: {final_job.exit_code}. "
            f"Check logs at {remote_output_file} and {remote_error_file}"
        ))

        return final_job

    async def list_simulation_outputs(
            self,
            job_id: str,
            ssh: SSHSession,
            simulation_output_dir: HPCFilePath,
            remote_output_file: HPCFilePath,
            final_job: SlurmJob | None,
            max_wait_seconds: int = 7200,
            poll_interval_seconds: int = 30,
            elapsed_seconds: int = 0,
    ) -> list[str]:

        # Verify simulation output files were created (using timeseries emitter)
        retcode, stdout, stderr = await ssh.run_command(
            f"find {simulation_output_dir.remote_path} -type f | head -5"
        )
        output_files = [f for f in stdout.strip().split("\n") if f]
        if not len(output_files) > 0: raise NextflowJobError(
            f"No output files found in output directory {simulation_output_dir.remote_path}. "
            f"Check logs at {remote_output_file}"
        )
        return output_files

    async def run_simulation(
            self,
            slurm_service: SlurmService,
            sms_ccam_main_real_nf: str,
            sms_ccam_workflow_config_real: str,
            nextflow_config_sms_ccam_real: str,
            slurm_template_nextflow_sms_ccam_real: str,
    ) -> list[str]:
        async with get_ssh_session_service().session() as ssh:
            submission = await self.submit_simulation_job(
                slurm_service=slurm_service,
                ssh=ssh,
                sms_ccam_workflow_config_real=sms_ccam_workflow_config_real,
                sms_ccam_main_real_nf=sms_ccam_main_real_nf,
                nextflow_config_sms_ccam_real=nextflow_config_sms_ccam_real,
                slurm_template_nextflow_sms_ccam_real=slurm_template_nextflow_sms_ccam_real
            )

            job_id = submission.job_id
            remote_output_file = submission.remote_output_file
            remote_error_file = submission.remote_error_file

            successful_job = await self.poll_simulation_job(
                job_id=job_id,
                slurm_service=slurm_service,
                ssh=ssh,
                remote_output_file=remote_output_file,
                remote_error_file=remote_error_file
            )

            outputs = await self.list_simulation_outputs(
                job_id=str(job_id),
                ssh=ssh,
                remote_output_file=remote_output_file,
                simulation_output_dir=submission.simulation_output_dir,
                final_job=successful_job,
            )

        return outputs