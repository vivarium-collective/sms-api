import json
from enum import StrEnum
from pathlib import Path
from typing import Any

import polars as pl

from sms_api.common.storage.file_paths import HPCFilePath
from sms_api.config import get_settings
from sms_api.data.models import SerializedArray


class OutputDataType(StrEnum):
    PARQUET = "history"
    ANALYSIS = "analyses"
    NEXTFLOW = "nextflow"
    SIMDATA = "parca"


def serialize_dataframe(df: pl.DataFrame) -> dict[str, SerializedArray]:
    dataframe = {}
    cols = df.columns
    for i, col in enumerate(df.iter_columns()):
        dataframe[cols[i]] = SerializedArray(col.to_numpy())
    return dataframe


def get_variant_data_dirpath(
    experiment_id: str,
    data_type: OutputDataType,
    variant: int,
    lineage_seed: int = 0,
    generation: int = 1,
    agent_id: int = 0,
    remote: bool = True,
) -> HPCFilePath:
    return (
        get_settings().simulation_outdir
        / experiment_id
        / data_type
        / f"experiment_id={experiment_id}"
        / f"variant={variant}"
        / f"lineage_seed={lineage_seed}"
        / f"generation={generation}"
        / f"agent_id={agent_id}"
    )


def write_json_for_slurm(data: dict[str, Any], outdir: Path, filename: str) -> Path:
    """Write dict to a JSON file accessible by SLURM jobs."""
    outdir.mkdir(parents=True, exist_ok=True)
    filepath = outdir / filename
    with filepath.open("w") as f:
        json.dump(data, f, indent=2)
    return filepath
