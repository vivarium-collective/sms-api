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
async def _():
    import marimo as mo

    from app.api.simulations import EcoliSim
    from sms_api.dependencies import init_standalone
    from sms_api.simulation import handlers, models

    # init services
    await init_standalone()

    return EcoliSim, handlers, mo, models


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
    mo.md(r"""#### Get simulatior versions""")
    return


@app.cell
async def _(handlers):
    simulator_versions = await handlers.get_simulator_versions()
    parca_versions = await handlers.get_parca_datasets()
    latest_simulator = await handlers.get_latest_simulator()
    return latest_simulator, parca_versions, simulator_versions


@app.cell
def _(latest_simulator, mo, models):
    def simulators_dropdown(simulator_versions: models.RegisteredSimulators) -> mo.ui.dropdown:
        opts = [f"{simulator.git_commit_hash}, {simulator.database_id}" for simulator in simulator_versions.versions]
        opts.append("latest")
        return mo.ui.dropdown(
            options=opts,
            # value=simulator_versions.versions[-1].git_commit_hash,
            value="latest",
            label="Select Simulator Version",
        )

    def parca_dropdown(parca_versions: list[models.ParcaDataset]):
        return mo.ui.dropdown(
            options=[
                f"{parca.database_id}, simulator: {parca.parca_dataset_request.simulator_version.git_commit_hash}"
                for parca in parca_versions
            ],
            label="Select Parca Version",
        )

    def run_simulation_button() -> mo.ui.run_button:
        return mo.ui.run_button(label="Run Single Cell Simulation")

    def latest_simulator_display() -> mo.json:
        return mo.json(data=latest_simulator.model_dump_json())

    def upload_simulator_button() -> mo.ui.run_button:
        return mo.ui.run_button(label="Upload Simulator")

    def run_parca_button() -> mo.ui.run_button:
        return mo.ui.run_button(label="Run Parca")

    return (
        latest_simulator_display,
        parca_dropdown,
        run_parca_button,
        run_simulation_button,
        simulators_dropdown,
        upload_simulator_button,
    )


@app.cell
def _(latest_simulator_display, mo, upload_simulator_button):
    latest_simulator_data = latest_simulator_display()
    upload_button = upload_simulator_button()
    mo.vstack([latest_simulator_data, upload_button])
    return (upload_button,)


@app.cell
def _(run_parca_button):
    parca_button = run_parca_button()
    parca_button
    return (parca_button,)


@app.cell
async def _(handlers, latest_simulator, upload_button):
    latest_simulator_version = None
    if upload_button.value:
        latest_simulator_version = await handlers.upload_simulator(commit_hash=latest_simulator.git_commit_hash)

    latest_simulator_version
    return (latest_simulator_version,)


@app.cell
async def _(handlers, latest_simulator_version, parca_button):
    latest_parca = None
    if parca_button.value:
        latest_parca = await handlers.run_parca(simulator=latest_simulator_version)

    latest_parca
    return


@app.cell
def _(
    mo,
    parca_dropdown,
    parca_versions,
    run_simulation_button,
    simulator_versions,
    simulators_dropdown,
):
    simulators = simulators_dropdown(simulator_versions)
    parca_datasets = parca_dropdown(parca_versions)
    simulation_run_button = run_simulation_button()

    mo.vstack([simulators, parca_datasets, simulation_run_button])
    return (simulation_run_button,)


@app.cell
async def _(
    handlers,
    parca_versions,
    simulation_run_button,
    simulator_versions,
):
    experiment = None
    if simulation_run_button.value:
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
