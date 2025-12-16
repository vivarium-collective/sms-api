# ================================= new implementation ================================================= #

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import override

from sms_api.analysis.analysis_service import AnalysisService, connect_ssh
from sms_api.analysis.models import AnalysisConfig, ExperimentAnalysisRequest, TsvOutputFile
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import Settings
from sms_api.simulation.hpc_utils import get_slurm_submit_file, get_slurmjob_name

__all__ = ["AnalysisServiceFS"]

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


MAX_ANALYSIS_CPUS = 5


class AnalysisServiceFS(AnalysisService):
    """Uses the "local" filesystem of remote to run vEcoli commands directly,
    as if it were local to the API gateway container. WARNING: this service
    is completely dependent on the NFS mount and should be used ONLY if remote
    execution is not available.
    """

    env: Settings

    @override
    async def dispatch_analysis(
        self,
        request: ExperimentAnalysisRequest,
        logger: logging.Logger,
        analysis_name: str,
        simulator_hash: str | None = None,
    ) -> tuple[None, int, AnalysisConfig]:
        # 1. create a vEcoli-complete JSON analysis config
        experiment_id = request.experiment_id
        analysis_config = request.to_config(analysis_name=analysis_name, env=self.env)
        # 1b. override config.analysis_options.outdir

        # 2a. create path ref to vEcoli/runscripts/analysis.py called analysis_script_path
        # 2b. create path ref to interpreter if needed
        # 3a. make analysis outdir in cache: os.mkdir(f"{REPO_ROOT}/.results_cache/{session_id}/{analysis_name}")
        # 3b. use subprocess to run and pipe the command: "uv run {analysis_script_path} --config {analysis_config!s}"
        # 4. continue with output retrieval

        return None, retcode, analysis_config

    @classmethod
    def run_command(cls, cmd: list[str]) -> int:
        """
        Run a subprocess command and stream its stdout/stderr to the logger in real-time.
        """
        # Start subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr into stdout
            text=True,  # get strings, not bytes
            bufsize=1,  # line-buffered
        )

        # Stream output line by line
        if process.stdout is not None:
            for line in process.stdout:
                logger.info(line.rstrip())  # live logging

        # Wait for process to finish
        retcode = process.wait()
        if retcode != 0:
            logger.error(f"Command {cmd} exited with {retcode}")
        return retcode

    @override
    async def get_available_output_paths(self, analysis_name: str) -> list[HPCFilePath]:
        """This should search locally, so env.analysis_outdir should be {REPO_ROOT}/.results_cache"""
        analysis_dirpath = Path(self.env.cache_dir) / analysis_name
        cmd = f'find "{analysis_dirpath!s}" -type f'
        if not self.ssh.connected:
            await self.ssh.connect()
        try:
            ret, out, err = await self.ssh.run_command(cmd)
            return [HPCFilePath(remote_path=Path(fp)) for fp in out.splitlines()]
        except Exception:
            logger.exception("could not get the filepaths that are available")
            return []

    @override
    async def download_analysis_output(
        self, local_cache_dir: Path, requested_filename: str, remote_path: HPCFilePath
    ) -> TsvOutputFile:
        local = local_cache_dir / requested_filename

        if not local.exists():
            await self.ssh.scp_download(local_file=local, remote_path=remote_path)
        verification = self.verify_result(local, 5)
        if not verification:
            logger.info("WARNING: resulting num cols/tps do not match requested.")
        file_content = local.read_text()
        output = TsvOutputFile(filename=requested_filename, content=file_content)
        return output

    def generate_script(
        self,
        slurm_log_file: HPCFilePath,
        slurm_job_name: str,
        latest_hash: str,
        config: AnalysisConfig,
        analysis_name: str,
    ) -> str:
        base_path = self.env.slurm_base_path.remote_path
        remote_workspace_dir = base_path / "workspace"
        vecoli_dir = remote_workspace_dir / "vEcoli"
        config_dir = vecoli_dir / "configs"

        qos_clause = f"#SBATCH --qos={self.env.slurm_qos}" if self.env.slurm_qos else ""
        nodelist_clause = f"#SBATCH --nodelist={self.env.slurm_node_list}" if self.env.slurm_node_list else ""

        return dedent(f"""\
            #!/bin/bash

            set -e

            ### set up java and nextflow
            local_bin=$HOME/.local/bin
            export JAVA_HOME=$local_bin/java-22
            export PATH=$JAVA_HOME/bin:$local_bin:$PATH
            ## export UV_PROJECT_ENVIRONMENT=disabled

            ### configure working dir and binds
            vecoli_dir={vecoli_dir!s}
            latest_hash={latest_hash}
            image=$HOME/workspace/images/vecoli-$latest_hash.sif
            vecoli_image_root=/vEcoli

            config_fp={config_dir!s}/{analysis_name}.json
            echo '{json.dumps(config.model_dump())}' > \"$config_fp\"

            cd $vecoli_dir

            ### binds
            binds="-B $HOME/workspace/vEcoli:/vEcoli"
            binds+=" -B $HOME/.local/share/uv:/root/.local/share/uv"
            binds+=" -B $HOME/workspace/api_outputs:/out"
            binds+=" -B $JAVA_HOME:$JAVA_HOME"
            binds+=" -B $HOME/.local/bin:$HOME/.local/bin"

            ### remove existing dir if needed and recreate
            analysis_outdir={config.analysis_options.outdir!s}
            if [ -d \"$analysis_outdir\" ]; then
                rm -rf \"$analysis_outdir\"
            fi
            mkdir -p {config.analysis_options.outdir!s}

            ### execute analysis
            singularity run $binds $image bash -c "
                export JAVA_HOME=$HOME/.local/bin/java-22
                export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
                uv run --no-cache --env-file /vEcoli/.env /vEcoli/runscripts/analysis.py --config \"$config_fp\"
            "

            ### optionally, remove uploaded fp
            rm -f \"$config_fp\"
        """)

    @connect_ssh
    async def submit_script(
        self, config: AnalysisConfig, experiment_id: str, script_content: str, slurm_job_name: str
    ) -> tuple[int, str, str, int]:
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                f.write(script_content)

            ssh_connected: bool = await self.ssh.verify_connection(retry=False)
            if not ssh_connected:
                logger.info(f"Warning: SSH is not connected in {__file__}.")
                await self.ssh.connect()

            return await self.script_service.execute_script(
                local_script_fp=local_submit_file, remote_script_fp=slurm_submit_file
            )

    def _collect_script_parameters(
        self, request: ExperimentAnalysisRequest, analysis_name: str, simulator_hash: str | None = None
    ) -> tuple[str, HPCFilePath]:
        # SLURM params
        job_name = get_slurmjob_name(
            experiment_id=analysis_name, simulator_hash=simulator_hash or get_simulator().git_commit_hash
        )
        log_file = self.env.slurm_log_base_path / f"{job_name}.out"
        return job_name, log_file
