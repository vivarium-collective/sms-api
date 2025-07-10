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
    import marimo as mo

    from app.api.simulations import EcoliSim
    from sms_api.dependencies import init_standalone
    from sms_api.simulation.models import RegisteredSimulators, SimulatorVersion, EcoliExperiment, EcoliSimulationRequest

    return EcoliSim, RegisteredSimulators, SimulatorVersion, mo


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
def _():
    import sms_api.api.client
    from sms_api.api.client.rest import ApiException
    from pprint import pprint

    configuration = sms_api.api.client.Configuration(
        host = "http://localhost:8888",
    )
    return ApiException, configuration, pprint, sms_api


@app.cell
def _(ApiException, SimulatorVersion, configuration, pprint, sms_api):
    # -- API Client calls -- #

    def on_run_simulation(simulator: dict, parca_dataset_id: str, variant_config: dict | None = None):
        with sms_api.api.client.ApiClient(configuration) as api_client:
            # Create an instance of the API class
            api_instance = sms_api.api.client.SimulationsApi(api_client)
            ecoli_simulation_request = sms_api.api.client.EcoliSimulationRequest(
                simulator=SimulatorVersion(**simulator),
                parca_dataset_id=parca_dataset_id,
                variant_config=variant_config or {}
            ) # EcoliSimulationRequest |

            try:
                # Run Antibiotics
                api_response = api_instance.run_simulation(ecoli_simulation_request=ecoli_simulation_request)
                print("The response of SimulationsApi->get_antibiotics_simulator_versions:\n")
                pprint(api_response)
            except ApiException as e:
                print("Exception when calling SimulationsApi->get_antibiotics_simulator_versions: %s\n" % e)


    def get_simulators():
        with sms_api.api.client.ApiClient(configuration) as api_client:
            # Create an instance of the API class
            api_instance = sms_api.api.client.SimulatorsApi(api_client)
            try:
                # Run Antibiotics
                api_response = api_instance.get_core_simulator_version()
                return api_response
            except ApiException as e:
                print("Exception when calling SimulatorsApi->get simulator Versions: %s\n" % e)


    def get_parcas():
        with sms_api.api.client.ApiClient(configuration) as api_client:
            # Create an instance of the API class
            api_instance = sms_api.api.client.SimulationsApi(api_client)
            try:
                # Run Antibiotics
                api_response = api_instance.get_parca_versions()
                return api_response
                return api_response
            except ApiException as e:
                print("Exception when calling SimulatorsApi->get simulator Versions: %s\n" % e)


    return get_parcas, get_simulators


@app.cell
def _(get_parcas):
    get_parcas()
    return


@app.cell
def _(RegisteredSimulators, mo):
    # -- marimio ui components -- #

    def simulators_dropdown(simulator_versions: RegisteredSimulators) -> mo.ui.dropdown:
        opts = [f"{simulator.git_commit_hash}, {simulator.database_id}" for simulator in simulator_versions.versions]
        opts.append("latest")
        return mo.ui.dropdown(
            options=opts,
            # value=simulator_versions.versions[-1].git_commit_hash,
            value="latest",
            label="Select Simulator Version",
        )

    def run_simulation_button() -> mo.ui.run_button:
        return mo.ui.run_button(label="Run Single Cell Simulation")


    def simulators_display(data: RegisteredSimulators) -> mo.ui.table:
        return mo.ui.table(
            data=data.model_dump()['versions'],
            selection="single",
            pagination=True
        )
    return run_simulation_button, simulators_display, simulators_dropdown


@app.cell
def _(get_simulators, simulators_display):
    simulator_versions = get_simulators()
    simulators_table = simulators_display(simulator_versions)
    simulators_table
    return (simulator_versions,)


@app.cell
def _(mo, run_simulation_button, simulator_versions, simulators_dropdown):
    simulators = simulators_dropdown(simulator_versions)
    simulation_run_button = run_simulation_button()

    mo.vstack([simulators, simulation_run_button])
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
