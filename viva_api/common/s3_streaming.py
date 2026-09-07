"""Backend-agnostic S3 -> tar.gz streaming helpers.

Lifted out of ``viva_api/common/handlers/simulations.py`` so both the study
route (``sms.py`` -> ``get_simulation_outputs``) and the compose route
(``compose.py`` -> ``get_results``) can stream an S3 prefix as a ``.tar.gz``
without ``compose.py`` (which stays deliberately thin/backend-agnostic) taking
on ``simulations.py``'s much heavier sms-specific import surface (simulation
services, ORM tables, an eager ``get_settings()`` call at import time, etc.).

Behavior is byte-for-byte identical to what used to live in
``simulations.py`` -- that module now imports these same functions from here,
so the study path's ``get_simulation_outputs``/``_stream_s3_tar_gz`` is
unaffected.
"""

import asyncio
import gzip
import io
import logging
import os
import tarfile
from collections.abc import AsyncIterator
from pathlib import Path

from viva_api.common.storage import data_layout
from viva_api.common.storage.file_paths import S3FilePath
from viva_api.dependencies import get_file_service

logger = logging.getLogger(__name__)


async def fetch_s3_file_entries(
    experiment_id: str, download_keys: list[str], experiment_prefix: str
) -> list[tuple[str, bytes]]:
    """Fetch S3 objects in-memory as (arcname, content) pairs for tar creation."""
    file_service = get_file_service()
    if file_service is None:
        raise RuntimeError("File service is not initialized")

    entries: list[tuple[str, bytes]] = []
    for key in download_keys:
        try:
            content = await file_service.get_file_contents(S3FilePath(s3_path=Path(key)))
            if content is not None:
                relative = str(Path(key).relative_to(experiment_prefix))
                entries.append((f"{experiment_id}/{relative}", content))
        except Exception:
            logger.warning(f"Failed to fetch {key}, skipping")
    return entries


def write_tar_entries(write_file: io.BufferedWriter, file_entries: list[tuple[str, bytes]]) -> None:
    """Write (arcname, content) pairs into a streaming tar archive."""
    try:
        with tarfile.open(fileobj=write_file, mode="w|") as tar:
            for arcname, data in file_entries:
                info = tarfile.TarInfo(name=arcname)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
    finally:
        write_file.close()


async def gzip_pipe_stream(
    read_file: io.BufferedReader, loop: asyncio.AbstractEventLoop, chunk_size: int
) -> AsyncIterator[bytes]:
    """Read raw tar data from a pipe, gzip-compress, and yield chunks."""
    gzip_buffer = io.BytesIO()
    gzip_file = gzip.GzipFile(fileobj=gzip_buffer, mode="wb")
    try:
        while True:
            raw = await loop.run_in_executor(None, read_file.read, chunk_size)
            if not raw:
                break
            gzip_file.write(raw)
            if gzip_buffer.tell() > 0:
                gzip_buffer.seek(0)
                compressed = gzip_buffer.read()
                gzip_buffer.seek(0)
                gzip_buffer.truncate()
                yield compressed
        gzip_file.close()
        gzip_buffer.seek(0)
        final = gzip_buffer.read()
        if final:
            yield final
    finally:
        read_file.close()


async def stream_s3_tar_gz_ray(experiment_id: str, chunk_size: int = 64 * 1024) -> AsyncIterator[bytes]:
    """Stream a Ray ensemble's S3 outputs (zarr stores + summaries) into a tar.gz.

        The Ray entrypoint syncs the whole ``.pbg/runs/phase0-xarray`` tree to
        ``s3://{bucket}/{s3_output_prefix}/{experiment_id}/`` -- for v2ecoli comparison
        runs that is ``v2ecoli_seed{NN}.zarr/`` per seed (each a hive-partitioned
        datatree of many small chunk objects; verified against ``sim61-v2c-*`` on
        smsvpctest) plus ``v2ecoli_build_config.json``. This function does not build
        those paths: unlike the Nextflow layout, we stream every object under the
        prefix as-is. (The per-seed store URI the observables reader targets is built
    by ``data_layout.RayLayout.seed_store_uri`` (the observables reader's path).)

    Also used by compose's Ray/Batch results route
    (``viva_api/api/routers/compose.py``): a compose sim's output and its
    chained analysis-job manifest (``analyses/<name>/_manifest.json``) both
    live under the same ``RayLayout.experiment_prefix(experiment_id)``, so
    streaming "every object under the prefix" captures both with no extra
    dispatch.
    """
    experiment_prefix = data_layout.RayLayout.experiment_prefix(experiment_id)

    file_service = get_file_service()
    if file_service is None:
        raise RuntimeError("File service is not initialized")

    listing = await file_service.get_listing(S3FilePath(s3_path=Path(experiment_prefix)))
    download_keys = [item.Key for item in listing]
    logger.info(f"Streaming {len(download_keys)} Ray output objects from S3 for experiment {experiment_id}")

    file_entries = await fetch_s3_file_entries(experiment_id, download_keys, experiment_prefix)

    read_fd, write_fd = os.pipe()
    read_file = os.fdopen(read_fd, "rb")
    write_file = os.fdopen(write_fd, "wb")
    loop = asyncio.get_event_loop()

    tar_future = loop.run_in_executor(None, write_tar_entries, write_file, file_entries)

    async for chunk in gzip_pipe_stream(read_file, loop, chunk_size):
        yield chunk

    await tar_future
