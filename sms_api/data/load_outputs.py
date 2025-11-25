import io
import tempfile
from enum import StrEnum
from typing import Literal

import polars
import polars as pl
import json
from pathlib import Path
import pickle

import pytest

from sms_api.common.ssh.ssh_service import get_ssh_service, SSHService
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import get_settings
from sms_api.data.models import SimulationOutputData


class OutputDataType(StrEnum):
    COMPLEXES = "complexes"
    METABOLIC_REACTIONS = "metabolic_reactions"
    MONOMERS = "monomers"
    RNAS = "rnas"
    BULK = "bulk"
    GENES = "genes"


def load(outdir: Path, output_type: OutputDataType) -> pl.LazyFrame:
    fp = outdir / f"wcm_{output_type}_MIX0-57.tsv"
    return pl.scan_csv(fp, comment_prefix="#", separator="\t")


def load_outputs(outdir: Path):
    return {
        dtype: load(outdir, dtype)
        for dtype in OutputDataType
    }


async def download_parquet(
    outdir_root: Path,
    expid: str,
    seed: int,
    output_type: OutputDataType,
    sim_name: str,
    tmpdir: tempfile.TemporaryDirectory,
    variant: int = 0
):
    outdir = outdir_root / expid / "analyses" / f"variant={variant}" / f"lineage_seed={seed}" / "plots"
    fname = f"{output_type}_{sim_name}.parquet"
    fp = outdir / fname
    remote = HPCFilePath(remote_path=fp)
    local = Path(tmpdir.name) / fname
    ssh = get_ssh_service()
    await ssh.scp_download(local_file=local, remote_path=remote)
    return local


async def load_seed_data(
    outdir_root: Path,
    expid: str,
    seed: int,
    output_type: OutputDataType,
    sim_name: str,
    tmpdir: tempfile.TemporaryDirectory,
    variant: int = 0,
    ssh: SSHService | None = None
):
    outdir = outdir_root / expid / "analyses" / f"variant={variant}" / f"lineage_seed={seed}" / "plots"
    fname = f"{output_type}_{sim_name}.parquet"
    fp = outdir / fname
    remote = HPCFilePath(remote_path=fp)
    # tmpdir = tempfile.TemporaryDirectory()
    local = Path(tmpdir.name) / fname
    ssh = ssh or get_ssh_service()
    await ssh.scp_download(local_file=local, remote_path=remote)
    df = pl.scan_parquet(local).collect()
    # tmpdir.cleanup()
    return df


async def load_seed(
    outdir_root: Path,
    expid: str,
    seed: int,
    sim_name: str,
    variant: int = 0,
    ssh: SSHService | None = None
) -> dict[str, str]:
    tmpdir = tempfile.TemporaryDirectory()
    data = {
        dtype: (await load_seed_data(
            outdir_root=outdir_root,
            expid=expid,
            sim_name=sim_name,
            seed=seed,
            variant=variant,
            output_type=dtype,
            tmpdir=tmpdir,
            ssh=ssh
        )).sort("time").to_pandas().to_json(orient="records")
        for dtype in [OutputDataType.BULK, OutputDataType.GENES]
    }
    tmpdir.cleanup()
    return data


def deserialize_dataframe(dtype: Literal["bulk", "genes"], data: SimulationOutputData) -> pl.DataFrame:
    json_str = getattr(data, dtype)
    return polars.read_json(io.BytesIO(json_str.encode("utf-8")))


@pytest.mark.asyncio
async def test_load_seed():
    env = get_settings()
    outdir_root = env.simulation_outdir.remote_path
    expid = "wcecoli_fig2_setD4_scaled-c6263425684df8c0_1763578699104-449b7de3d0de10a5_1763578788396"
    sim_id = "wcecoli_figure2_setD4"
    seed = 3
    variant = 0
    data = await load_seed(
        outdir_root=outdir_root,
        expid=expid,
        seed=seed,
        sim_name=sim_id,
        variant=variant
    )
    print(data)


