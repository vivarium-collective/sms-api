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

    import json
    from pprint import pp

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
    from app.api.plots import plot_from_dfs
    from app.api.client_wrapper import ClientWrapper


    base_url = "http://localhost:8888/core"
    client = ClientWrapper(base_url=base_url)
    return (
        Chart,
        Client,
        EcoliExperiment,
        EcoliSim,
        EcoliSimulationRequest,
        ParcaDataset,
        WorkerEvent,
        base_url,
        client,
        json,
        mo,
        pl,
    )


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
    client,
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
                response = client.post(f"{base_url}/simulation/run", json=payload)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(e)


    def on_get_status(simulation_id: int) -> dict:
        client.get_simulation_status(simulation_id=simulation_id)


    def on_get_events(simulation_id: int) -> list[dict]:
        with Client() as client:
            try:
                response = client.get(f"{base_url}/simulation/run/events")
                response.raise_for_status()
                return response.json()
            except:
                raise Exception(f"Could not get the simulation status using simulation_id: {simulation_id}.")

    return on_get_events, on_get_parcas, on_run_simulation


@app.cell
def _(on_get_parcas):
    parcas = on_get_parcas()
    request_payload = {
        'parca_dataset_id': parcas[-1]['database_id'],
        'simulator': parcas[-1]['parca_dataset_request']['simulator_version'],
        'variant_config': {
            "named_parameters": {"param1": 0.5, "param2": 0.5}
        }
    }

    return (request_payload,)


@app.cell
def _():
    # param_name = mo.ui.text(placeholder="Parameter Name")
    # variant_config = mo.ui.dictionary({"parameter": param_name})
    return


@app.cell
def _(EcoliSimulationRequest, request_payload):
    simulation_request = EcoliSimulationRequest(**request_payload)
    return (simulation_request,)


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
):
    simulation_events = None
    if experiment is not None and check_status_button.value:
        simulation_events = on_get_events(simulation_id=experiment['simulation']['database_id'])

    simulation_events
    return (simulation_events,)


@app.cell
def _(Chart, WorkerEvent, pl, plot_from_df):
    # 1. get simulation events
    # 2. index needed cols as necessary
    # 3. load #2 into a polars df
    # 4. call plot

    def plot_data(worker_event: WorkerEvent) -> Chart:
        df = pl.DataFrame(data=worker_event.sim_data)
        return plot_from_df(dataframe=df)

    return


@app.cell
def update_data(mo, pl, simulation_events):
    # Simulate receiving new data (in practice, stream this in)
    new_data = None
    if simulation_events is not None:
        new_data = pl.DataFrame(simulation_events[-1]['sim_data'])
        # Append to growing stateful history
        mo.state.df_history = mo.state.df_history.vstack(new_data, in_place=False)
    return


@app.cell
def _():
    # fig1 = None
    # if simulation_run_button.value:
    #     simulator_version = select_simulator(simulator_versions.versions, latest_simulator, simulators.selected_key)
    #     print(f"Running with simulator version: {simulator_version}")
    #     sim1 = EcoliSim()
    #     sim1.simulate_single_cell()
    #     fig1 = sim1.display_single_cell_mass_fractions()
    #
    # fig1
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    ### Batch simulation

    This runs the variants workflow
    """
    )
    return


@app.cell
def _(mo):
    sim2_n_cells = mo.ui.slider(1, 50, value=10, label="Number of Cells")
    sim2_run_button = mo.ui.run_button(label="Run Simulation")

    mo.vstack([sim2_n_cells, sim2_run_button])
    return sim2_n_cells, sim2_run_button


@app.cell
def _(EcoliSim, sim2_n_cells, sim2_run_button):
    fig2 = None
    if sim2_run_button.value:
        sim2 = EcoliSim()
        sim2.simulate_multiple_cells(n_cells=sim2_n_cells.value)
        fig2 = sim2.display_multi_cell_total_masses()
    fig2
    return


if __name__ == "__main__":
    app.run()
