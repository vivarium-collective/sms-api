import json
import logging
import tempfile
import zipfile
from collections.abc import Generator
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import Settings, get_settings
from sms_api.data.models import AnalysisConfig
from sms_api.simulation.hpc_utils import get_slurm_submit_file, get_slurmjob_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_ANALYSIS_CPUS = 5


async def dispatch(
    config: AnalysisConfig, analysis_name: str, simulator_hash: str, env: Settings, logger: logging.Logger
) -> tuple[str, int]:
    experiment_id = config.analysis_options.experiment_id[0]
    slurmjob_name = get_slurmjob_name(experiment_id=experiment_id, simulator_hash=simulator_hash)
    base_path = Path(env.slurm_base_path)
    slurm_log_file = base_path / f"prod/htclogs/{slurmjob_name}.out"

    slurm_script = _slurm_script(
        slurm_log_file=slurm_log_file,
        slurm_job_name=slurmjob_name,
        env=env,
        latest_hash=simulator_hash,
        config=config,
        analysis_name=analysis_name,
        # experiment_id=experiment_id,
    )

    with open("assets/example_analysis_slurm.sh", "w") as outfile:
        outfile.write(slurm_script)

    ssh = get_ssh_service(env)
    slurmjob_id = await _submit_script(
        config=config,
        experiment_id=experiment_id,
        script_content=slurm_script,
        slurm_job_name=slurmjob_name,
        env=env,
        ssh=ssh,
    )

    return slurmjob_name, slurmjob_id


def _slurm_script(
    slurm_log_file: Path,
    slurm_job_name: str,
    env: Settings,
    latest_hash: str,
    config: AnalysisConfig,
    analysis_name: str,
) -> str:
    base_path = Path(env.slurm_base_path)
    remote_workspace_dir = base_path / "workspace"
    vecoli_dir = remote_workspace_dir / "vEcoli"
    config_dir = vecoli_dir / "configs"
    conf = config.model_dump_json() or "{}"
    experiment_id = config.analysis_options.experiment_id[0]

    return dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={slurm_job_name}
        #SBATCH --time=30:00
        #SBATCH --cpus-per-task {MAX_ANALYSIS_CPUS}
        #SBATCH --mem=8GB
        #SBATCH --partition={env.slurm_partition}
        #SBATCH --qos={env.slurm_qos}
        #SBATCH --output={slurm_log_file!s}
        #SBATCH --nodelist={env.slurm_node_list}

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
        uv run --no-cache python $HOME/workspace/scripts/write_config.py \
          --name {analysis_name} \
          --config_path "$tmp_config"

        cd $vecoli_dir

        ### binds
        binds="-B $HOME/workspace/vEcoli:/vEcoli"
        binds+=" -B $HOME/workspace/api_outputs:/out"
        binds+=" -B $JAVA_HOME:$JAVA_HOME"
        binds+=" -B $HOME/.local/bin:$HOME/.local/bin"

        image=$HOME/workspace/images/vecoli-$latest_hash.sif
        vecoli_image_root=/vEcoli

        mkdir -p {remote_workspace_dir!s}/api_outputs/{analysis_name}
        singularity run $binds $image bash -c "
            export JAVA_HOME=$HOME/.local/bin/java-22
            export PATH=$JAVA_HOME/bin:$HOME/.local/bin:$PATH
            uv run --env-file /vEcoli/.env /vEcoli/runscripts/analysis.py --config \"$tmp_config\"
        "
        cd {remote_workspace_dir!s}
        uv run python scripts/archive_dir.py {remote_workspace_dir!s}/api_outputs/{analysis_name}
    """)


async def _submit_script(
    config: AnalysisConfig,
    experiment_id: str,
    script_content: str,
    slurm_job_name: str,
    env: Settings,
    ssh: SSHService | None = None,
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

        base_path = Path(env.slurm_base_path)
        remote_workspace_dir = base_path / "workspace"
        vecoli_dir = remote_workspace_dir / "vEcoli"
        config_dir = vecoli_dir / "configs"

        slurm_jobid = await slurm_service.submit_job(
            local_sbatch_file=local_submit_file, remote_sbatch_file=slurm_submit_file
        )
        return slurm_jobid


# -- utils -- #


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


def get_html_output_paths(outdir_root: Path, experiment_id: str) -> list[Path]:
    outdir = outdir_root / experiment_id
    filepaths = []
    for root, _, files in outdir.walk():
        for f in files:
            fp = root / f
            if fp.exists() and fp.is_file():
                filepaths.append(fp)
    return list(filter(lambda _file: _file.name.endswith(".html"), filepaths))


def read_html_file(file_path: Path) -> str:
    """Read an HTML file and return its contents as a single string."""
    with open(str(file_path), encoding="utf-8") as f:
        return f.read()


def get_analysis_html_outputs(outdir_root: Path, expid: str = "analysis_multigen") -> list[str]:
    filepaths = get_html_output_paths(outdir_root, expid)
    return [read_html_file(path) for path in filepaths]
