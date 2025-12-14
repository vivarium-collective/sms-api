# -- utils -- #


import functools
import io
import json
import tempfile
import zipfile
from collections.abc import Awaitable, Coroutine, Generator
from io import BytesIO
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable
from zipfile import ZIP_DEFLATED, ZipFile

import polars
from typing_extensions import Concatenate

from sms_api.common.ssh.ssh_service import SSHService, SSHServiceManaged
from sms_api.data.models import OutputFile, P, R, TsvOutputFile


def connect_ssh(
    func: Callable[Concatenate[Any, P], Awaitable[R]],
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
            kwargs.get("ssh_service") if not getattr(instance, "ssh_service", None) else instance.ssh_service  # type: ignore[assignment]
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
