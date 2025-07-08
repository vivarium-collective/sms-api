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
    import httpx
    import marimo as mo

    from client.api.antibiotic import EcoliSim
    from sms_api.simulation.models import RegisteredSimulators, Simulator, SimulatorVersion

    return (
        EcoliSim,
        RegisteredSimulators,
        Simulator,
        SimulatorVersion,
        httpx,
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
async def _(RegisteredSimulators, Simulator, httpx, mo):
    @mo.lru_cache
    async def get_simulators() -> RegisteredSimulators:
        # return await get_simulator_versions()
        with httpx.Client() as client:
            resp = client.get("http://localhost:8888/core/simulator/versions")
            resp.raise_for_status()
            return RegisteredSimulators(**resp.json())

    @mo.lru_cache
    async def get_latest_simulator() -> Simulator:
        with httpx.Client() as client:
            resp = client.get("http://localhost:8888/core/simulator/latest")
            resp.raise_for_status()
            return Simulator(**resp.json())

    simulator_versions = await get_simulators()
    latest_simulator = await get_latest_simulator()
    return latest_simulator, simulator_versions


@app.cell
def _(RegisteredSimulators, Simulator, SimulatorVersion, httpx, mo):
    def select_simulator(
        simulators: list[SimulatorVersion], latest_simulator: Simulator, commit_hash: str
    ) -> SimulatorVersion:
        if commit_hash == "latest":
            with httpx.Client() as client:
                latest_version = client.post(
                    url="http://localhost:8888/core/simulator/upload", json=latest_simulator.model_dump()
                )
                return latest_version
        try:
            return next(filter(lambda sim: sim.git_commit_hash == commit_hash, simulators))
        except StopIteration:
            raise ValueError("Couldnt find that simulator!")

    def simulators_dropdown(simulator_versions: RegisteredSimulators) -> mo.ui.dropdown:
        opts = [simulator.git_commit_hash for simulator in simulator_versions.versions]
        opts.append("latest")
        return mo.ui.dropdown(
            options=opts,
            # value=simulator_versions.versions[-1].git_commit_hash,
            value="latest",
            label="Select Simulator Version",
        )

    def run_simulation_button() -> mo.ui.run_button:
        return mo.ui.run_button(label="Run Single Cell Simulation")

    return run_simulation_button, select_simulator, simulators_dropdown


@app.cell
def _(mo, run_simulation_button, simulator_versions, simulators_dropdown):
    simulators = simulators_dropdown(simulator_versions)
    simulation_run_button = run_simulation_button()

    mo.vstack([simulators, simulation_run_button])
    return simulation_run_button, simulators


@app.cell
def _(
    EcoliSim,
    latest_simulator,
    select_simulator,
    simulation_run_button,
    simulator_versions,
    simulators,
):
    fig1 = None
    if simulation_run_button.value:
        simulator_version = select_simulator(simulator_versions.versions, latest_simulator, simulators.selected_key)
        print(f"Running with simulator version: {simulator_version}")
        sim1 = EcoliSim()
        sim1.simulate_single_cell()
        fig1 = sim1.display_single_cell_mass_fractions()

    fig1
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
