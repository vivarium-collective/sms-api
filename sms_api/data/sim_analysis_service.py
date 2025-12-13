import abc
import io
import json
import logging
import tempfile
import zipfile
import functools
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import override, Any, Awaitable, TypeVar, Callable, Coroutine
from zipfile import ZIP_DEFLATED, ZipFile
from typing_extensions import ParamSpec, Concatenate

import polars

from sms_api.common.gateway.utils import get_simulator
from sms_api.common.hpc.slurm_service import SlurmServiceManaged
from sms_api.common.models import DataId
from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged, get_ssh_service_managed
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.common.utils import unique_id, get_uuid
from sms_api.config import get_settings, Settings
from sms_api.data.models import AnalysisConfig, OutputFile, TsvOutputFile, ExperimentAnalysisRequest
from sms_api.simulation.hpc_utils import get_slurm_submit_file, get_slurmjob_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


MAX_ANALYSIS_CPUS = 5

P = ParamSpec("P")
R = TypeVar("R")


# ================================= new implementation ================================================= #

class AnalysisService(abc.ABC):
    env: Settings
    ssh: SSHServiceManaged

    def __init__(self, env: Settings | None = None, env_file_path: Path | None = None):
        self.env = env or get_settings(env_file_path)
        self.ssh = get_ssh_service_managed()

    @abc.abstractmethod
    async def dispatch_analysis(
        self,
        request: ExperimentAnalysisRequest,
        logger: logging.Logger,
        simulator_hash: str | None = None,
        analysis_name: str | None = None
    ) -> tuple[str, int]:
        pass

    @classmethod
    def generate_analysis_name(cls, experiment_id: str | None = None, _n_sections: int = 1) -> str:
        return get_uuid(
            scope="analysis",
            data_id=experiment_id,
            n_sections=_n_sections
        )


class AnalysisServiceHpc(AnalysisService):
    @override
    async def dispatch_analysis(
        self,
        request: ExperimentAnalysisRequest,
        logger: logging.Logger,
        simulator_hash: str | None = None,
        analysis_name: str | None = None
    ) -> tuple[str, int]:
        # collect params
        (experiment_id,
         analysis_name,
         analysis_config,
         slurmjob_name,
         slurm_log_file) = self._collect_parameters(
            request=request,
            simulator_hash=simulator_hash
        )

        # gen script
        slurm_script = self.generate_slurm_script(
            slurm_log_file=slurm_log_file,
            slurm_job_name=slurmjob_name,
            latest_hash=simulator_hash,
            config=analysis_config,
            analysis_name=analysis_name,
        )

        # submit script
        slurmjob_id = await self.submit_slurm_script(
            config=analysis_config,
            experiment_id=experiment_id,
            script_content=slurm_script,
            slurm_job_name=slurmjob_name,
            ssh=self.ssh,
        )

        return slurmjob_name, slurmjob_id

    def _collect_parameters(
        self,
        request: ExperimentAnalysisRequest,
        simulator_hash: str | None = None
    ) -> tuple[str, str, AnalysisConfig, str, HPCFilePath]:
        # vEcoli workflow params
        experiment_id = request.experiment_id
        analysis_name = self.generate_analysis_name()  # self.generate_analysis_name(experiment_id)
        analysis_config = request.to_config(analysis_name=analysis_name, env=self.env)

        # SLURM params
        slurmjob_name = get_slurmjob_name(experiment_id=analysis_name, simulator_hash=simulator_hash or get_simulator().git_commit_hash)
        slurm_log_file = self.env.slurm_log_base_path / f"{slurmjob_name}.out"
        return experiment_id, analysis_name, analysis_config, slurmjob_name, slurm_log_file

    def generate_slurm_script(
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
        nodelist_clause = (
            f"#SBATCH --nodelist={self.env.slurm_node_list}" if self.env.slurm_node_list else ""
        )

        return dedent(f"""\
            #!/bin/bash
            #SBATCH --job-name={slurm_job_name}
            #SBATCH --time=30:00
            #SBATCH --cpus-per-task {MAX_ANALYSIS_CPUS}
            #SBATCH --mem=8GB
            #SBATCH --partition={self.env.slurm_partition}
            {qos_clause}
            #SBATCH --output={slurm_log_file!s}
            {nodelist_clause}

            set -e

            ### set up java and nextflow
            local_bin=$HOME/.local/bin
            export JAVA_HOME=$local_bin/java-22
            export PATH=$JAVA_HOME/bin:$local_bin:$PATH
            ## export UV_PROJECT_ENVIRONMENT=disabled

            ### configure working dir and binds
            vecoli_dir={vecoli_dir!s}
            latest_hash={latest_hash}
            
            config_fp={config_dir!s}/{analysis_name}.json
            echo '{json.dumps(config.model_dump())}' > \"$config_fp\"

            cd $vecoli_dir

            ### binds
            binds="-B $HOME/workspace/vEcoli:/vEcoli"
            binds+=" -B $HOME/.local/share/uv:/root/.local/share/uv"
            binds+=" -B $HOME/workspace/api_outputs:/out"
            binds+=" -B $JAVA_HOME:$JAVA_HOME"
            binds+=" -B $HOME/.local/bin:$HOME/.local/bin"

            image=$HOME/workspace/images/vecoli-$latest_hash.sif
            vecoli_image_root=/vEcoli

            mkdir -p {config.analysis_options.outdir!s}
            singularity run $binds $image bash -c "
                export JAVA_HOME=$HOME/.local/bin/java-22
                export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
                uv run --no-cache --env-file /vEcoli/.env /vEcoli/runscripts/analysis.py --config \"$config_fp\"
            "
        """)

    async def submit_slurm_script(
            self,
            config: AnalysisConfig,
            experiment_id: str,
            script_content: str,
            slurm_job_name: str,
            ssh: SSHServiceManaged,
    ) -> int:
        slurm_service = SlurmServiceManaged(ssh_service=self.ssh)
        slurm_submit_file = get_slurm_submit_file(slurm_job_name=slurm_job_name)

        with tempfile.TemporaryDirectory() as tmpdir:
            local_submit_file = Path(tmpdir) / f"{slurm_job_name}.sbatch"
            with open(local_submit_file, "w") as f:
                f.write(script_content)

            ssh_connected = await slurm_service.ssh_service.verify_connection()
            slurm_jobid = await slurm_service.submit_job(
                local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
            )
            return slurm_jobid


# -- utils -- #


def connect_ssh(
    func: Callable[Concatenate["AnalysisService", P], Awaitable[R]]
) -> Callable[[tuple[Any, ...], dict[str, Any]], Coroutine[Any, Any, Any]]:
    """
    Decorator for classes that rely on a persistent "sticky" SSH service connection
        for long-running tasks, like analyses.

    :param func: (Callable) Instance method of which this func wraps.
    :return:
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        instance = args[0]
        ssh_service: SSHServiceManaged = (
            kwargs.get("ssh_service") if not getattr(instance, "ssh_service", None)
            else instance.ssh_service  # type: ignore[assignment]
        )
        # ssh_service = kwargs.get('ssh_service', get_ssh_service_managed())
        try:
            print(f"Connecting ssh for function: {func.__name__}!")
            await ssh_service.connect()
            print(f"Connected: {ssh_service.connected}")
            return await func(*args, **kwargs)
        finally:
            print(f"Disconnecting ssh for function: {func.__name__}!")
            await ssh_service.disconnect()
            print(f"Connected: {ssh_service.connected}")

    return wrapper


def get_experiment_id_from_tag(experiment_tag: str) -> str:
    parts = experiment_tag.split("-")
    parts.remove(parts[-1])
    return "-".join(parts)


def get_analysis_dir(outdir: Path, experiment_id: str) -> Path:
    return outdir / experiment_id / "analyses"


def get_analysis_paths(analysis_dir: Path) -> set[Path]:
    paths = set()
    for root, _, files in analysis_dir.walk():
        for fname in files:
            fp = root / fname
            if fp.exists():
                paths.add(fp)
    return paths


def generate_zip_buffer(file_paths: list[tuple[Path, str]]) -> Generator[Any]:
    """
    Generator function to stream a zip file dynamically.
    """
    # Use BytesIO as an in-memory file-like object for chunks
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
        for file_path, arcname in file_paths:
            # arcname is the filename inside the zip (can handle non-unique names)
            zip_file.write(file_path, arcname=arcname)
    buffer.seek(0)
    yield from buffer


def unzip_archive(zip_path: Path, dest_dir: Path) -> str:
    zip_path = Path(zip_path).resolve()
    dest_dir = Path(dest_dir).resolve()

    if not zip_path.is_file():
        raise FileNotFoundError(f"{zip_path} does not exist or is not a file")

    if not dest_dir.is_dir():
        raise NotADirectoryError(f"{dest_dir} does not exist or is not a directory")

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(dest_dir)

    return str(dest_dir)


async def get_tsv_outputs_local(output_id: str, ssh_service: SSHService) -> list[OutputFile]:
    """Run in DEV"""
    remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
    ret, stdin, stdout = await ssh_service.run_command(
        dedent(f"""
                cd /home/FCAM/svc_vivarium/workspace \
                    && {remote_uv_executable} run scripts/ptools_outputs.py --output_id {output_id}
            """)
    )

    deserialized = json.loads(stdin.replace("'", '"'))
    outputs = []
    for spec in deserialized:
        output = OutputFile(name=spec["name"], content=spec["content"])
        outputs.append(output)
    return outputs


async def get_tsv_manifest_local(output_id: str, ssh_service: SSHService) -> list[TsvOutputFile]:
    """Run in DEV"""
    remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
    ret, stdin, stdout = await ssh_service.run_command(
        dedent(f"""
                cd /home/FCAM/svc_vivarium/workspace \
                    && {remote_uv_executable} run scripts/ptools_outputs.py --output_id {output_id} --manifest
            """)
    )

    deserialized = json.loads(stdin.replace("'", '"'))
    return [TsvOutputFile(**item) for item in deserialized]


async def get_html_outputs_local(output_id: str, ssh_service: SSHServiceManaged) -> list[OutputFile]:
    """Run in DEV"""
    remote_uv_executable = "/home/FCAM/svc_vivarium/.local/bin/uv"
    ret, stdin, stdout = await ssh_service.run_command(
        dedent(f"""
                cd /home/FCAM/svc_vivarium/workspace \
                    && {remote_uv_executable} run scripts/html_outputs.py --output_id {output_id}
            """)
    )

    deserialized = json.loads(stdin.replace("'", '"'))
    outputs = []
    for spec in deserialized:
        output = OutputFile(name=spec["name"], content=spec["content"])
        outputs.append(output)
    return outputs


def format_tsv_string(output: OutputFile) -> str:
    raw_string = output.content
    return raw_string.encode("utf-8").decode("unicode_escape")


def format_html_string(output: OutputFile) -> str:
    raw_string = output.content
    return raw_string.encode("utf-8").decode("unicode_escape")


def tsv_string_to_polars_df(output: OutputFile) -> polars.DataFrame:
    formatted = format_tsv_string(output)
    return polars.read_csv(io.StringIO(formatted), separator="\t")


def write_tsvs(data: list[OutputFile]) -> None:
    lines = [(output.name, "".join(output.content).split("\n")) for output in data]
    with tempfile.TemporaryDirectory() as tmpdir:
        for filename, filedata in lines:
            with open(Path(tmpdir) / filename, "w") as f:
                for item in filedata:
                    f.write(f"{item}\n")
