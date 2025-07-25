import marimo

__generated_with = "0.14.11"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    mo._runtime.context.get_context().marimo_config["runtime"]["output_max_bytes"] = 10000000000
    return


@app.cell
def _():
    import abc 
    import os 
    import asyncssh
    import logging
    import re
    from asyncssh import SSHCompletedProcess
    from pathlib import Path 

    import polars as pl
    import altair as alt 
    import numpy as np

    from sms_api.config import get_settings
    from sms_api.common.gateway.models import Namespace
    from sms_api.common.ssh.ssh_service import get_ssh_service
    from sms_api.simulation.models import BaseModel

    logger = logging.getLogger(__file__)
    settings = get_settings()

    results_dir_root = Path(__file__).parent.parent.parent / "results"
    return Path, pl


@app.cell
def _(Path, pl):
    def get_experiment_dirpath(experiment_id: str) -> Path:
        """Get the remote (uchc hpc) dirpath of a given simulation's chunked parquet outputs"""
        return Path(f"/home/FCAM/svc_vivarium/prod/sims/{experiment_id}/history/experiment_id={experiment_id}/variant=0/lineage_seed=0/generation=1/agent_id=0")


    def get_local_experiment_dirpath() -> Path:
        return Path('/Users/alexanderpatrie/Desktop/repos/ecoli/sms-api/results/prod/experiment_78c6310_id_149_20250723-112814/history/experiment_id=experiment_78c6310_id_149_20250723-1112814/variant=0/lineage_seed=0/generation=1/agent_id=0')

    def serialize_df(df: pl.DataFrame) -> bytes:
        return df.serialize(format='json')

    def hydrate_df(serialized: bytes | str) -> pl.DataFrame:
        import io
        if isinstance(serialized, bytes):
            buff = io.BytesIO(serialized) 
            buff_format = "bytes"
        else:
            buff = io.StringIO(serialized)
            buff_format = "json"
        return pl.DataFrame.deserialize(buff, format=buff_format)
    
    def get_results(experiment_id: str | None = None, observable_names: list[str] | None = None, experiment_dirpath: Path | None = None) -> pl.LazyFrame:
        # get experiment dirpath
        experiment_dirpath = experiment_dirpath or get_experiment_dirpath(experiment_id)
        lf = pl.scan_parquet(experiment_dirpath)
        if observable_names is not None:
            return lf.select(*observable_names)
        return lf

    # def collect(experiment_id: str | None = None, observable_names: list[str] | None = None, experiment_dirpath: Path | None = None) ->:
    #     pass

    return get_local_experiment_dirpath, get_results, hydrate_df, serialize_df


@app.cell
def _(get_local_experiment_dirpath, get_results):
    experiment_id = "experiment_78c6310_id_149_20250723-112814"
    experiment_dirpath = get_local_experiment_dirpath()
    selected_observables = ["bulk"]
    lf = get_results(experiment_dirpath=experiment_dirpath, observable_names=selected_observables)
    return (lf,)


@app.cell
def _(lf):
    df = lf.collect()
    return


@app.cell
def _(pl):
    data = pl.DataFrame({'x': 11.11, 'y': 22, 'z': 0.3})
    return (data,)


@app.cell
def _(data, serialize_df):
    serialized = serialize_df(data, )
    serialized
    return (serialized,)


@app.cell
def _(hydrate_df, serialized):
    dataframe = hydrate_df(serialized)
    dataframe
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
