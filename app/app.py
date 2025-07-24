import marimo

__generated_with = "0.14.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import json
    import os
    import subprocess
    import uuid
    from pathlib import Path

    import numpy as np
    import polars as pl

    def format_simdata_path(tmpdir: str):
        return f"{tmpdir}/kb/simData.cPickle"

    class SimulationService:
        def __init__(self, config_dir=None):
            self.config_dir = config_dir or Path("/Users/alexanderpatrie/Desktop/repos/ecoli/vEcoli/configs")

        def get_config(self, config_id: str, **overrides) -> dict:
            config_fp = self.config_dir / f"{config_id}.json"

            with open(config_fp) as f:
                workflow_config = json.load(f)

            if overrides:
                for param_name, param in overrides.items():
                    workflow_config[param_name] = param

            return workflow_config

        def get_simulation_process(self, config_id: str, duration: float | None = None, step_size: float | None = None):
            # with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = "out"
            print(f"RUNNING TEMPDIR: {tmpdir}")

            # adjust config and write to temp
            times = np.arange(0.0, duration or 2528.0, step_size or 1.0).tolist()
            experiment_id = f"api_{str(uuid.uuid4()).split('-')[-1]}"
            workflow_config = self.get_config(
                config_id=config_id,
                experiment_id=experiment_id,
                # emitter_arg={"out_dir": tmpdir},
                # daughter_outdir=tmpdir,
                # parca_options={"outdir": tmpdir},
                # sim_data_path=format_simdata_path(tmpdir)
            )
            config_fp = os.path.join(tmpdir, f"{config_id}.json")
            with open(config_fp, "w") as f:
                json.dump(workflow_config, f)

            # run cmd for workflow
            cmd = f"uv run runscripts/workflow.py --config {config_fp}"
            try:
                proc = subprocess.Popen(cmd)
                return proc
            except subprocess.CalledProcessError as e:
                print(e)

        def run_simulation(
            self, config_id: str, duration: float | None = None, step_size: float | None = None
        ) -> pl.DataFrame:
            # with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = "out"
            print(f"RUNNING TEMPDIR: {tmpdir}")

            # adjust config and write to temp
            times = np.arange(0.0, duration or 2528.0, step_size or 1.0).tolist()
            experiment_id = f"api_{str(uuid.uuid4()).split('-')[-1]}"
            workflow_config = self.get_config(
                config_id=config_id,
                experiment_id=experiment_id,
                # emitter_arg={"out_dir": tmpdir},
                # daughter_outdir=tmpdir,
                # parca_options={"outdir": tmpdir},
                # sim_data_path=format_simdata_path(tmpdir)
            )
            config_fp = os.path.join(tmpdir, f"{config_id}.json")
            with open(config_fp, "w") as f:
                json.dump(workflow_config, f)

            # run cmd for workflow
            cmd = f"uv run runscripts/workflow.py --config {config_fp}"
            try:
                proc = subprocess.Popen(cmd)
                proc.wait()
                subprocess.run(cmd.split(" "), check=True)
            except subprocess.CalledProcessError as e:
                print(e)

            # removed adjusted config
            os.remove(config_fp)
            # get chunks data
            experiment_id = workflow_config.get("experiment_id")
            chunks_dir = (
                Path(tmpdir)
                / experiment_id
                / "history"
                / f"experiment_id={experiment_id}"
                / "variant=0/lineage_seed=0/generation=1/agent_id=0"
            )
            if os.path.exists(chunks_dir):
                return pl.read_parquet(chunks_dir).sort("time")
            else:
                raise FileNotFoundError(f"{chunks_dir} not found!!!")

    def test_service():
        service = SimulationService()
        config_id = "api"
        df = service.run_simulation(config_id=config_id)
        return df

    return SimulationService, pl, subprocess


@app.cell
def _():
    # df = test_service()
    return


@app.cell
def _():
    import duckdb

    # Create a DuckDB connection
    duckdb_conn = duckdb.connect(":memory:")
    return (duckdb_conn,)


@app.cell
def _(df):
    df.columns
    return


@app.cell
def _(df, pl):
    listeners_cols = [col for col in df.columns if col.startswith("listeners__mass")]
    query = f"SELECT {', '.join(listeners_cols)} FROM df"
    querydf = pl.DataFrame({"query": query})
    return


@app.cell
def _(df, duckdb_conn, mo):
    data = mo.sql(
        """
        select time, listeners__mass__growth from df limit 1111
        """,
        engine=duckdb_conn,
    )
    return (data,)


@app.cell
def _(data):
    data.plot.line(x="time", y="listeners__mass__growth")
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ```bash
    # Running a simulation with nextflow and dynamically plotting/interpreting result data:

    module1: runsim()

    module2(marimo): while((true) => {
        chunks_dir = getdir()
        df = pl.read_parquet(chunks_dir)
    })


    uv run module1 & uv run module2
    ```
    """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ```bash
    # Running num_simulations in parallel:

    parallelProcess: run n simulations in parallel(() -> {
        n = num_simulations
        runsim() & runsim() & ...(n) & runsim()
    })






    ```
    """
    )
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ### Running simulations in parallel

    ```python
    # run_cmd = f"poetry run python {runsim_module_path} --perturbation_config={perturbation_params}"
    ```
    """
    )
    return


@app.cell
def _(SimulationService, config_path, proc):
    def run_batch(n_simulations: int, config_ids: list[str], perturbation_params: dict | None = None):
        # TODO: for perturbations, dynamically make new configs iteratively and pass into command rather than as arg
        runsim_module_path = "/Users/alexanderpatrie/Desktop/repos/ecoli/vEcoli/api/runscripts/workflow.py"
        run_cmd = f"uv run python {runsim_module_path} --config {config_path!s}"
        procs = []
        for n in range(n_simulations):
            # executed_cmd += f" & {run_cmd}"
            proc_n = SimulationService().get_simulation_process(config_ids[0])
            procs.append(proc)

        for proc in procs:
            proc.wait()

    return


@app.cell
def _(format_command):
    format_command(3)
    return


@app.cell
def _(n, subprocess):
    procs = []
    for v in range(n):
        # cmd = ["runsim", f"--params=p{i}"]
        cmd = ["which", "poetry"]
        proc = subprocess.Popen(cmd)
        procs.append(proc)

    # Wait for all to complete
    for proc in procs:
        proc.wait()
    return (proc,)


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
