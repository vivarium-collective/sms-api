import io
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

import polars

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService, get_ssh_service
from sms_api.config import Settings, get_settings
from sms_api.data.models import AnalysisConfig, OutputFile, TsvOutputFile
from sms_api.simulation.hpc_utils import get_slurm_submit_file, get_slurmjob_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MAX_ANALYSIS_CPUS = 5


async def dispatch(
    config: AnalysisConfig, analysis_name: str, simulator_hash: str, env: Settings, logger: logging.Logger
) -> tuple[str, int]:
    # experiment_id = config.analysis_options.experiment_id[0]
    slurmjob_name = get_slurmjob_name(experiment_id=analysis_name, simulator_hash=simulator_hash)
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

    ssh = get_ssh_service(env)
    slurmjob_id = await _submit_script(
        config=config,
        experiment_id=config.analysis_options.experiment_id[0],
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
    # config_dir = vecoli_dir / "configs"
    # conf = config.model_dump_json() or "{}"
    # experiment_id = config.analysis_options.experiment_id[0]

    return dedent(f"""\
        #!/bin/bash
        #SBATCH --job-name={slurm_job_name}
        #SBATCH --time=30:00
        #SBATCH --cpus-per-task {MAX_ANALYSIS_CPUS}
        #SBATCH --mem=10GB
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

        # base_path = Path(env.slurm_base_path)
        # remote_workspace_dir = base_path / "workspace"
        # vecoli_dir = remote_workspace_dir / "vEcoli"
        # config_dir = vecoli_dir / "configs"

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


def get_tsv_output_paths_remote(experiment_id: str) -> list[Path]:
    outdir_root = Path("/home/FCAM/svc_vivarium/workspace/api_outputs")
    outdir = outdir_root / experiment_id
    filepaths = []
    for root, _, files in outdir.walk():
        for f in files:
            fp = root / f
            if fp.exists() and fp.is_file():
                filepaths.append(fp)
    return list(filter(lambda _file: _file.name.endswith(".txt"), filepaths))


def get_tsv_manifest_remote(output_id: str) -> list[TsvOutputFile]:
    import re

    # outdir_root = Path("/home/FCAM/svc_vivarium/workspace/api_outputs")
    paths = [str(fp) for fp in get_tsv_output_paths_remote(output_id)]
    outputs = []
    for p in paths:
        match = re.search(r"experiment_id=[^/]+/(.*)", p)
        if match:
            result = match.group(1)
            filename = Path(result).name
            metadata_components = result.replace(f"/{filename}", "").split("/")
            md = {}
            for comp in metadata_components:
                scope, scope_id = comp.split("=")
                md[scope] = int(scope_id)
            md["filename"] = filename  # type: ignore[assignment]
            outputs.append(md)
            # outputs.append({"metadata": metadata_components, "filename": filename})
    return [TsvOutputFile(**item) for item in outputs]  # type: ignore[arg-type]


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


def read_tsv_file(file_path: Path) -> str:
    """Read an HTML file and return its contents as a single string."""
    with open(str(file_path), encoding="utf-8") as f:
        return f.read()


def get_tsv_outputs_remote(output_id: str = "analysis_multigen") -> list[OutputFile]:
    """Run in PROD"""

    def get_tsv_output_paths(outdir_root: Path, experiment_id: str) -> list[Path]:
        outdir = outdir_root / experiment_id
        filepaths = []
        for root, _, files in outdir.walk():
            for f in files:
                fp = root / f
                if fp.exists() and fp.is_file():
                    filepaths.append(fp)
        return list(filter(lambda _file: _file.name.endswith(".txt"), filepaths))

    def read_tsv_file(file_path: Path) -> str:
        """Read an HTML file and return its contents as a single string."""
        with open(str(file_path), encoding="utf-8") as f:
            return f.read()

    outdir_root = Path("/home/FCAM/svc_vivarium/workspace/api_outputs")
    filepaths = get_tsv_output_paths(outdir_root, output_id)

    files = []
    for path in filepaths:
        file_id = f"{path.name.replace('.txt', '')}_{path.parent.parts[-1]}"
        outfile = OutputFile(name=file_id, content=read_tsv_file(path))
        files.append(outfile)

    sorted_files = sorted(files, key=lambda o: int(o.name.split("=")[-1]))
    return sorted_files


async def get_html_outputs_local(output_id: str, ssh_service: SSHService) -> list[OutputFile]:
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


def get_html_outputs_remote(output_id: str = "analysis_multigen") -> list[OutputFile]:
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

    outdir_root = Path("/home/FCAM/svc_vivarium/workspace/api_outputs")
    filepaths = get_html_output_paths(outdir_root, output_id)

    files = []
    for path in filepaths:
        file_id = f"{path.name.replace('.html', '')}_{path.parent.parts[-1]}"
        outfile = OutputFile(name=file_id, content=read_html_file(path))
        files.append(outfile)

    return files


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
