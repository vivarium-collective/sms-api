import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl
from fastapi import BackgroundTasks

from sms_api.common.ssh.ssh_service import get_ssh_service
from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.simulation.models import BaseModel, ObservablesRequest


async def upload_data_asset(local: Path | str, remote: HPCFilePath | str) -> None:
    if isinstance(local, str):
        local = Path(local)
    if isinstance(remote, str):
        remote = HPCFilePath(remote_path=Path(remote))
    ssh = get_ssh_service()
    await ssh.scp_upload(local, remote)


class SimulationOutputData(BaseModel):
    experiment_id: str
    bulk: str
    genes: str


@dataclass
class TransformData:
    experiment_id: str
    bulk: pl.LazyFrame | pl.DataFrame
    genes: pl.LazyFrame | pl.DataFrame

    def to_dto(self) -> SimulationOutputData:
        assets: list[str] = [self.experiment_id]
        for data in [self.bulk, self.genes]:
            if isinstance(data, pl.LazyFrame):
                data = data.collect()
            assets.append(data.to_pandas().to_json())
        return SimulationOutputData(**dict(zip(["experiment_id", "bulk", "genes"], assets)))


async def download_transforms(
    expid: str, remote_outdir_root: Path, observables: ObservablesRequest, bg_tasks: BackgroundTasks, **partition: Any
) -> SimulationOutputData:
    partition_spec = "/".join(list(map(lambda p: f"{p[0]}={p[1]}", [(key, val) for key, val in partition.items()])))
    remote_outdir = Path(remote_outdir_root) / expid / partition_spec
    ssh_service = get_ssh_service()

    dto_kwargs = {}
    local_dir = tempfile.TemporaryDirectory()
    bg_tasks.add_task(local_dir.cleanup)
    for obs_type in ["bulk", "genes"]:
        fname = f"{obs_type}_{expid}.parquet"
        remote_path = HPCFilePath(remote_path=remote_outdir / fname)
        local_path = Path(local_dir.name) / fname
        # download the pq locally
        await ssh_service.scp_download(local_file=local_path, remote_path=remote_path)
        # load the local path download data
        lf_obs: pl.LazyFrame = pl.scan_parquet(local_path)
        specified = getattr(observables, obs_type)
        colname = f"{obs_type}_molecules" if obs_type == "bulk" else "gene names" if obs_type == "genes" else None
        if len(specified):
            dto_kwargs[obs_type] = (
                lf_obs.select([colname, "time"]).sort("time").filter(pl.col(colname).is_in(specified))  # type: ignore[arg-type]
            )
    return TransformData(**dto_kwargs, experiment_id=expid).to_dto()
