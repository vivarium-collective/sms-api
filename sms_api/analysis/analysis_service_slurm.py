# ================================= new implementation ================================================= #
import asyncio
import dataclasses
import hashlib
import json
import logging
import tempfile
from collections.abc import Awaitable
from functools import wraps
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable

import pandas as pd

from sms_api.analysis.models import (
    AnalysisConfig,
    AnalysisRun,
    ExperimentAnalysisDTO,
    ExperimentAnalysisRequest,
    JobStatus,
    TsvOutputFile,
)
from sms_api.common.gateway.utils import get_simulator
from sms_api.common.hpc.slurm_service import SlurmServiceManaged
from sms_api.common.ssh.ssh_service import SSHServiceManaged, get_ssh_service_managed
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import Settings
from sms_api.simulation.hpc_utils import get_slurm_submit_file, get_slurmjob_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_ANALYSIS_CPUS = 4
MAX_ANALYSIS_MEM = "24GB"


@dataclasses.dataclass
class RequestPayload:
    data: dict[str, Any]

    def hash(self) -> str:
        normalized = normalize_json(self.data)
        b_rep = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(b_rep).hexdigest()


def connect_ssh(func: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    @wraps(func)
    async def wrapper(self: "AnalysisServiceSlurm", **kwargs: Any) -> Any:
        try:
            if self.ssh.connected:
                raise RuntimeError()
            await self.ssh.connect()
            return await func(self, **kwargs)
        finally:
            await self.ssh.disconnect()

    return wrapper


def normalize_json(obj: Any) -> Any:
    """Recursively sort dict keys in JSON-like object."""
    if isinstance(obj, dict):
        return {k: normalize_json(obj[k]) for k in sorted(obj)}
    elif isinstance(obj, list):
        return [normalize_json(x) for x in obj]
    else:
        return obj


class AnalysisServiceSlurm:
    env: Settings
    ssh: SSHServiceManaged

    def __init__(self, env: Settings):
        self.env = env
        self.ssh = get_ssh_service_managed(self.env)

    @property
    def slurm_service(self) -> SlurmServiceManaged:
        return SlurmServiceManaged(ssh_service=self.ssh)

    async def dispatch_analysis(
        self,
        request: ExperimentAnalysisRequest,
        logger: logging.Logger,
        analysis_name: str,
        simulator_hash: str | None = None,
    ) -> tuple[str, int, AnalysisConfig]:
        # collect params
        slurmjob_name, slurm_log_file = self._collect_slurm_parameters(
            request=request, simulator_hash=simulator_hash, analysis_name=analysis_name
        )
        experiment_id = request.experiment_id
        analysis_config = request.to_config(analysis_name=analysis_name, env=self.env)

        # gen script
        slurm_script = generate_slurm_script(
            env=self.env,
            slurm_log_file=slurm_log_file,
            slurm_job_name=slurmjob_name,
            latest_hash=simulator_hash or get_simulator().git_commit_hash,
            config=analysis_config,
            analysis_name=analysis_name,
        )

        # submit script
        slurmjob_id = await self._submit_slurm_script(
            config=analysis_config,
            experiment_id=experiment_id,
            script_content=slurm_script,
            slurm_job_name=slurmjob_name,
        )
        return slurmjob_name, slurmjob_id, analysis_config

    async def poll_status(self, dto: ExperimentAnalysisDTO) -> AnalysisRun:
        db_id = dto.database_id
        identifier = dto.job_id
        if identifier is None:
            raise ValueError("There is no job id yet associated with this record.")

        await asyncio.sleep(3)
        run = await self.get_analysis_status(job_id=identifier, db_id=db_id)
        while run.status.lower() not in ["completed", "failed"]:
            await asyncio.sleep(3)
            run = await self.get_analysis_status(job_id=identifier, db_id=db_id)
        if run.status.lower() == "failed":
            raise Exception(f"Analysis Run has failed:\n{run}")
        return run

    async def get_available_output_paths(self, remote_analysis_outdir: HPCFilePath) -> list[HPCFilePath]:
        cmd = f'find "{remote_analysis_outdir!s}" -type f'
        if not self.ssh.connected:
            await self.ssh.connect()
        try:
            ret, out, err = await self.ssh.run_command(cmd)
            return [HPCFilePath(remote_path=Path(fp)) for fp in out.splitlines()]
        except Exception:
            logger.exception("could not get the filepaths that are available")
            return []

    async def download_analysis_output(self, local_dir: Path, remote_path: HPCFilePath) -> TsvOutputFile:
        requested_filename = remote_path.remote_path.parts[-1]
        if not requested_filename.endswith(".txt"):
            logger.info(f"wrong filename: {requested_filename}")
        local = local_dir / requested_filename

        if not local.exists():
            await self.ssh.scp_download(local_file=local, remote_path=remote_path)

        # verification = self._verify_result(local, 5)
        # if not verification:
        #     logger.info("WARNING: resulting num cols/tps do not match requested.")

        file_content = local.read_text()
        output = TsvOutputFile(filename=requested_filename, content=file_content)
        return output

    async def get_analysis_status(self, job_id: int, db_id: int) -> AnalysisRun:
        slurmjob_id = job_id
        slurm_user = self.env.slurm_submit_user
        ssh_service = self.ssh
        if not ssh_service.connected:
            await ssh_service.connect()

        try:
            statuses = await ssh_service.run_command(f"sacct -u {slurm_user} | grep {slurmjob_id}")
        except Exception:
            statuses = await ssh_service.run_command(f"sacct -j {slurmjob_id}")
        finally:
            status: str = statuses[1].split("\n")[0].split()[-2]
        return AnalysisRun(id=db_id, status=JobStatus[status])

    @classmethod
    def _verify_result(cls, local_result_path: Path, expected_n_tp: int) -> bool:
        tsv_data = pd.read_csv(local_result_path, sep="\t")
        actual_cols = [col for col in tsv_data.columns if col.startswith("t")]
        return len(actual_cols) == expected_n_tp

    def _generate_slurm_script(
        self,
        slurm_log_file: HPCFilePath,
        slurm_job_name: str,
        latest_hash: str,
        config: AnalysisConfig,
        analysis_name: str,
    ) -> str:
        return generate_slurm_script(
            env=self.env,
            slurm_log_file=slurm_log_file,
            slurm_job_name=slurm_job_name,
            latest_hash=latest_hash,
            config=config,
            analysis_name=analysis_name,
        )

    @connect_ssh
    async def _submit_slurm_script(
        self, config: AnalysisConfig, experiment_id: str, script_content: str, slurm_job_name: str
    ) -> int:
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                f.write(script_content)

            ssh_connected: bool = await self.slurm_service.ssh_service.verify_connection(retry=False)
            if not ssh_connected:
                logger.info(f"Warning: SSH is not connected in {__file__}.")
                await self.slurm_service.ssh_service.connect()

            slurm_jobid = await self.slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid

    def _collect_slurm_parameters(
        self, request: ExperimentAnalysisRequest, analysis_name: str, simulator_hash: str | None = None
    ) -> tuple[str, HPCFilePath]:
        # SLURM params
        slurmjob_name = get_slurmjob_name(
            experiment_id=analysis_name, simulator_hash=simulator_hash or get_simulator().git_commit_hash
        )
        slurm_log_file = self.env.slurm_log_base_path / f"{slurmjob_name}.out"
        # return experiment_id, analysis_name, analysis_config, slurmjob_name, slurm_log_file

        return slurmjob_name, slurm_log_file


def generate_slurm_script(
    env: Settings,
    slurm_log_file: HPCFilePath,
    slurm_job_name: str,
    latest_hash: str,
    config: AnalysisConfig,
    analysis_name: str,
) -> str:
    base_path = env.slurm_base_path.remote_path
    remote_workspace_dir = base_path / "workspace"
    vecoli_dir = remote_workspace_dir / "vEcoli"
    config_dir = vecoli_dir / "configs"
    qos_clause = f"#SBATCH --qos={env.slurm_qos}" if env.slurm_qos else ""
    nodelist_clause = f"#SBATCH --nodelist={env.slurm_node_list}" if env.slurm_node_list else ""
    slurm_err_file = str(slurm_log_file.remote_path).replace(".out", ".err")
    return dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={slurm_job_name}
        #SBATCH --time=30:00
        #SBATCH --cpus-per-task {MAX_ANALYSIS_CPUS}
        #SBATCH --mem={MAX_ANALYSIS_MEM}
        #SBATCH --partition={env.slurm_partition}
        {qos_clause}
        #SBATCH --mail-type=ALL
        {nodelist_clause}
        #SBATCH -o {slurm_log_file!s}
        #SBATCH -e {slurm_err_file}

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


# class CacheService:
#     @classmethod
#     def normalize_request_json(cls, serialized_request: dict[str, Any]) -> Any:
#         obj = serialized_request
#         if isinstance(obj, dict):
#             return {k: cls.normalize_request_json(obj[k]) for k in sorted(obj)}
#         elif isinstance(obj, list):
#             return [cls.normalize_request_json(x) for x in obj]
#         else:
#             return obj
#
#     def get_redis_client(self):
#         return redis.from_url(
#             "redis://redis:6379",
#             decode_responses=True,
#             max_connections=100,
#         )
#
#     async def get_text_result(self, redis_client, job_id: str) -> str:
#         cache_key = f"job:text:{job_id}"
#
#         # 1️⃣ Try Redis cache first
#         cached = await redis_client.get(cache_key)
#         if cached:
#             return cached
#
#         # 2️⃣ If not cached (cold), read from object storage
#         def download():
#             pass
#
#         obj = download()  # e.g., S3/MinIO
#         text = obj.read().decode()
#
#         # 3️⃣ Cache it for next time (hot cache)
#         if len(text) < 256_000:
#             await redis_client.setex(cache_key, 600, text)  # TTL 10 min
#
#         # 4️⃣ Return the text
#         return text
