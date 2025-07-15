import marimo

__generated_with = "0.14.10"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(
        r"""
    # EcoliSim: Interactive Simulation Interface
    Welcome to **EcoliSim**, a browser-based interface for running and analyzing whole-cell *E. coli* simulations. This notebook is powered by [Marimo](https://github.com/marimo-team/marimo) and provides lightweight access to *E. coli* models relevant to microbial dynamics, biomanufacturing, and antibiotic response.

    Use the controls in each section to simulate growth, visualize outcomes, and explore parameter spaces.
    """
    )
    return


@app.cell
def _():
    # 1. upload simulator
    # 2. upload parca
    # 3. pin {simulator_id: ..., parca_id: ...}
    # 4. run simulation using #3

    import os
    import json
    from pprint import pp
    from pathlib import Path

    import marimo as mo
    import polars as pl
    from altair import Chart
    from fastapi import HTTPException
    from httpx import AsyncClient, QueryParams, Client

    from sms_api.simulation.models import (
        SimulatorVersion,
        EcoliSimulationRequest,
        EcoliExperiment,
        WorkerEvent,
        ParcaDataset
    )
    from app.api.simulations import EcoliSim
    from app.api.plots import plot_mass_fractions
    from app.api.client_wrapper import ClientWrapper


    base_url = "http://localhost:8888/core"
    client = ClientWrapper(base_url=base_url)
    return (
        Client,
        EcoliExperiment,
        EcoliSimulationRequest,
        ParcaDataset,
        Path,
        base_url,
        json,
        mo,
        os,
        pl,
        plot_mass_fractions,
    )


@app.cell
def _(Path, os, pl):
    # this block should simulate the worker events coming in, where in this example, each chunk file can represent
    #    a chunk of worker events being streamed


    mass_columns = {
        "Protein": "listeners__mass__protein_mass",
        "tRNA": "listeners__mass__tRna_mass",
        "rRNA": "listeners__mass__rRna_mass",
        "mRNA": "listeners__mass__mRna_mass",
        "DNA": "listeners__mass__dna_mass",
        "Small Mol.s": "listeners__mass__smallMolecule_mass",
        "Dry": "listeners__mass__dry_mass",
        "Time": "time"
    }

    chunks_dir = Path("assets/tests/test_history")
    chunk_paths = iter(sorted(
        [str(chunks_dir / fname) for fname in os.listdir(chunks_dir)],
        key=lambda p: int(p.split("/")[-1].removesuffix(".pq"))
    ))
    # Get just the column names
    mass_column_names = list(mass_columns.values())

    # Read and select only the desired columns from each file
    chunk_data = [
        pl.read_parquet(fp).select(mass_column_names)
        for fp in chunk_paths
    ]

    # Concatenate into a single DataFrame
    simulation_df = pl.concat(chunk_data)
    return (simulation_df,)


@app.cell
def _(mo):
    if not hasattr(mo.state, "dataframes"):
        mo.state.dataframes = []
    if not hasattr(mo.state, "current_index"):
        mo.state.current_index = 0

    step_size = 10  # number of rows to append per button press
    plt_button = mo.ui.run_button(label="Plot Mass Fractions")
    return plt_button, step_size


@app.cell
def _(mo, pl, plot_mass_fractions, plt_button, simulation_df, step_size):
    if plt_button.value:
        next_index = mo.state.current_index
        end_index = min(next_index + step_size, simulation_df.height)
        if next_index < simulation_df.height:
            mo.state.dataframes.append(simulation_df.slice(next_index, end_index - next_index))
            mo.state.current_index = end_index

    # Display chart
    def display_chart():
        if mo.state.dataframes:
            combined_df = pl.concat(mo.state.dataframes)
            chart = plot_mass_fractions(dataframes=[combined_df])
            return mo.vstack([plt_button, chart])
        else:
            return mo.vstack([plt_button, mo.md("Press the button to start streaming.")])

    display_chart()
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ## E. coli core

    This section provides tools to simulate basic E. coli growth models, both as single-cell simulations and batch simulations.

    Use these models to understand baseline physiology and stochastic variability across replicates.
    """
    )
    return


@app.cell
def _(mo):
    mo.md(r"""### Single cell simulation""")
    return


@app.cell
def _(mo):
    mo.md(r"""#### Get simulator versions""")
    return


@app.cell
def _(
    Client,
    EcoliExperiment,
    EcoliSimulationRequest,
    ParcaDataset,
    base_url,
    json,
    mo,
):
    # -- API Client calls -- #
    @mo.cache
    def on_get_parcas() -> list[ParcaDataset]:
        with Client() as client:
            try:
                response = client.get(f"{base_url}/simulation/parca/versions")
                response.raise_for_status()
                return response.json()
            except:
                raise Exception(f"Could not get the parca datasets.")


    def on_run_simulation(request: EcoliSimulationRequest) -> EcoliExperiment:
        with Client() as client:
            payload = json.loads(request.model_dump_json())  # use the param, not global
            try:
                response = client.post(
                    url=f"{base_url}/simulation/run",
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(e)


    def on_get_status(simulation_id: int) -> dict:
        with Client() as client:
            try:
                response = client.post(
                    url=f"{base_url}/simulation/status",
                    params={"simulation_id": simulation_id}
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(e)


    def on_get_events(simulation_id: int) -> list[dict]:
        with Client() as client:
            try:
                response = client.get(
                    url=f"{base_url}/simulation/run/events",
                    params={"simulation_id": simulation_id}
                )
                response.raise_for_status()
                return response.json()
            except:
                raise Exception(f"Could not get the simulation status using simulation_id: {simulation_id}.")

    return on_get_events, on_get_parcas, on_get_status, on_run_simulation


@app.cell
def _(EcoliSimulationRequest, on_get_parcas):
    parcas = on_get_parcas()
    request_payload = {
        'parca_dataset_id': parcas[-1]['database_id'],
        'simulator': parcas[-1]['parca_dataset_request']['simulator_version'],
        'variant_config': {
            "named_parameters": {"param1": 0.5, "param2": 0.5}
        }
    }
    simulation_request = EcoliSimulationRequest(**request_payload)
    simulation_request
    return (simulation_request,)


@app.cell
def _():
    # param_name = mo.ui.text(placeholder="Parameter Name")
    # variant_config = mo.ui.dictionary({"parameter": param_name})
    return


@app.cell
def _(mo):
    run_simulation_button = mo.ui.run_button(label="Run Simulation")
    run_simulation_button
    return (run_simulation_button,)


@app.cell
def _(
    EcoliExperiment,
    on_run_simulation,
    run_simulation_button,
    simulation_request,
):
    experiment: EcoliExperiment | None = None
    if run_simulation_button.value:
        experiment = on_run_simulation(request=simulation_request)
    return (experiment,)


@app.cell
def _(experiment: "EcoliExperiment | None", mo):
    experiment_table = mo.ui.table(data=[experiment])
    experiment_table
    return


@app.cell
def _(experiment: "EcoliExperiment | None"):
    experiment
    return


@app.cell
def _(mo):
    check_status_button = mo.ui.run_button(label="Check Simulation Status")
    check_status_button
    return (check_status_button,)


@app.cell
def _(
    check_status_button,
    experiment: "EcoliExperiment | None",
    on_get_events,
    on_get_status,
):
    simulation_events = None
    simulation_status = None
    if experiment is not None and check_status_button.value:
        simulation_id = experiment['simulation']['database_id']
        simulation_status = on_get_status(simulation_id=simulation_id)
        simulation_events = on_get_events(simulation_id=simulation_id)

    simulation_events
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
