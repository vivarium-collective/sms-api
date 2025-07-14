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

    from pprint import pp

    from httpx import AsyncClient, QueryParams, Client
    import marimo as mo
    from fastapi import HTTPException

    from sms_api.simulation.models import SimulatorVersion, EcoliSimulationRequest, EcoliExperiment
    from app.api.simulations import EcoliSim


    base_url = "http://localhost:8888/core"
    return (
        Client,
        EcoliSim,
        EcoliSimulationRequest,
        HTTPException,
        base_url,
        mo,
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
def _():
    return


@app.cell
def _(Client, EcoliSimulationRequest, HTTPException, base_url, mo):
    # -- API Client calls -- #
    @mo.cache
    def on_get_latest_simulator():
        with Client() as client:
            try:
                response = client.get(url=f"{base_url}/simulator/latest")
                response.raise_for_status()
                return response.json()
            except:
                raise HTTPException("Could not get the simulator versions.")


    @mo.cache
    def on_get_simulators():
        with Client() as client:
            try:
                response = client.get(url=f"{base_url}/simulator/versions")
                response.raise_for_status()
                return response.json()
            except:
                raise HTTPException("Could not get the simulator versions.")


    def on_run_simulation(request: EcoliSimulationRequest):
        with Client() as client:
            # Create an instance of the API class
            try:
                response = client.post(url=f"{base_url}/simulation/run", json=request.model_dump())
                response.raise_for_status()
                return response.json()
            except:
                raise HTTPException("Could not get the simulator versions.")

    return on_get_latest_simulator, on_get_simulators


@app.cell
def _(on_get_latest_simulator):
    latest_simulator = on_get_latest_simulator()
    latest_simulator
    return


@app.cell
def _(mo):
    get_simulators_button = mo.ui.run_button(label="Get simulators")
    get_simulators_button
    return (get_simulators_button,)


@app.cell
def _(get_simulators_button, mo, on_get_simulators):
    simulators_table = None
    if get_simulators_button.value:
        simulators = on_get_simulators()
        simulators_table = mo.ui.table(data=simulators["versions"])
        print(simulators)

    simulators_table
    return


@app.cell
def _(mo):
    run_sim_button = mo.ui.run_button(label="Run Simulation")
    run_sim_button
    return


@app.cell
def _(mo):
    simulation_request = mo.ui.dictionary()
    return


@app.cell
async def _(
    handlers,
    parca_versions,
    run_sim_button_button,
    simulator_versions,
):
    experiment = None
    if run_sim_button_button.value:
        experiment = await handlers.run_simulation(
            simulator=simulator_versions.versions[0], parca_dataset=parca_versions[0]
        )

    experiment
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
