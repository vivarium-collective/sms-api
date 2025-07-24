import marimo

__generated_with = "0.14.11"
app = marimo.App(width="medium")


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

    def get_results(experiment_id: str | None = None, observable_names: list[str] | None = None, experiment_dirpath: Path | None = None) -> pl.LazyFrame:
        # get experiment dirpath
        experiment_dirpath = experiment_dirpath or get_experiment_dirpath(experiment_id)
        lf = pl.scan_parquet(experiment_dirpath)
        if observable_names is not None:
            return lf.select(*observable_names)
        return lf

    return get_local_experiment_dirpath, get_results


@app.cell
def _(get_local_experiment_dirpath, get_results):
    experiment_id = "experiment_78c6310_id_149_20250723-112814"
    experiment_dirpath = get_local_experiment_dirpath()
    print(experiment_dirpath)
    lf = get_results(experiment_dirpath=experiment_dirpath, observable_names=["bulk"])
    return (lf,)


@app.cell
def _(lf):
    lf.collect()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
