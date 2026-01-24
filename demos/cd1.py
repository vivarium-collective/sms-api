import marimo

__generated_with = "0.19.4"
app = marimo.App(width="full")


@app.cell
def _():  # noqa: C901
    import time
    from enum import StrEnum

    import httpx

    from sms_api.analysis.models import TsvOutputFile
    from sms_api.common.simulator_defaults import DEFAULT_BRANCH, DEFAULT_REPO
    from sms_api.simulation.models import Simulation, Simulator, SimulatorVersion

    class BaseUrl(StrEnum):
        LOCAL = "http://localhost:8888"
        ACADEMIC_PROD = "https://sms.cam.uchc.edu"
        ACADEMIC_DEV = "https://sms-dev.cam.uchc.edu"
        STANFORD = "http://localhost:8080"

    BASE_URL = BaseUrl.STANFORD

    class E2EDataService:
        client: httpx.Client

        def __init__(self, base_url: BaseUrl, timeout: int = 300) -> None:
            self.client = httpx.Client(base_url=base_url, timeout=timeout)

        def _submit_get_latest_simulator(self, repo_url: str | None = None, branch: str | None = None):
            try:
                latest_response = self.client.get(
                    url="/core/v1/simulator/latest",
                    params={"git_branch": branch or DEFAULT_BRANCH, "git_repo_url": repo_url or DEFAULT_REPO},
                )
                return Simulator(**latest_response.json())
            except Exception as e:
                raise httpx.HTTPError(e)

        def _submit_upload_simulator(self, simulator: Simulator):
            try:
                uploaded_response = self.client.post(url="/core/v1/simulator/upload", json=simulator.model_dump())
                return SimulatorVersion(**uploaded_response.json())
            except Exception as e:
                raise httpx.HTTPError(e)

        def _submit_get_simulator_build_status(self, simulator: SimulatorVersion) -> str:
            try:
                status_update_response = self.client.get(
                    url="/core/v1/simulator/status", params={"simulator_id": simulator.database_id}
                )
                if status_update_response.status_code != 200:
                    raise httpx.HTTPError("Error!")  # noqa: TRY301
                return status_update_response.json().get("status")
            except Exception as e:
                raise httpx.HTTPError(e)

        def _submit_run_workflow(
            self,
            experiment_id: str,
            simulator_id: int,
            config_filename: str,
            num_generations: int,
            num_seeds: int,
            description: str,
        ) -> Simulation:
            try:
                simulation_response = self.client.post(
                    url="/api/v1/simulations",
                    params={
                        "simulator_id": simulator_id,
                        "simulation_config_filename": config_filename,
                        "num_generations": num_generations,
                        "num_seeds": num_seeds,
                        "description": description,
                        "experiment_id": experiment_id,
                    },
                )
                return Simulation(**simulation_response.json())
            except Exception as e:
                raise httpx.HTTPError(e)

        def _submit_get_workflow_status(self, simulation_id: int) -> str:
            try:
                status_update_response = self.client.get(url=f"/api/v1/simulations/{simulation_id}/status")
                if status_update_response.status_code != 200:
                    raise httpx.HTTPError("Error!")  # noqa: TRY301
                return status_update_response.json().get("status")
            except Exception as e:
                raise httpx.HTTPError(e)

        def _submit_get_output_data(self, simulation_id: int) -> list[TsvOutputFile]:
            try:
                data_response = self.client.post(url=f"/api/v1/simulations/{simulation_id}/data")
                if data_response.status_code != 200:
                    raise httpx.HTTPError("Error!")  # noqa: TRY301
                return [TsvOutputFile(**output) for output in data_response.json()]
            except Exception as e:
                raise httpx.HTTPError(e)

        def get_simulator(self) -> SimulatorVersion:
            latest = self._submit_get_latest_simulator()
            uploaded = self._submit_upload_simulator(simulator=latest)
            status = "pending"
            try:
                while status not in ["completed", "failed"]:
                    status = self._submit_get_simulator_build_status(simulator=uploaded)
                    time.sleep(1.0)
            except Exception as e:
                raise httpx.HTTPError(e)
            return uploaded

        def run_workflow(
            self,
            experiment_id: str,
            simulator_id: int,
            config_filename: str,
            num_generations: int,
            num_seeds: int,
            description: str,
        ) -> Simulation:
            simulation = self._submit_run_workflow(
                config_filename=config_filename,
                experiment_id=experiment_id,
                simulator_id=simulator_id,
                num_generations=num_generations,
                num_seeds=num_seeds,
                description=description,
            )
            return simulation

        def get_workflow_status(self, simulation_id: int) -> str:
            status = self._submit_get_workflow_status(simulation_id=simulation_id)
            return status

        def get_output_data(self, simulation_id: int) -> list[TsvOutputFile]:
            outputs = self._submit_get_output_data(simulation_id=simulation_id)
            return outputs

    return BASE_URL, E2EDataService, TsvOutputFile


@app.cell
def _(BASE_URL, E2EDataService):
    e2e = E2EDataService(base_url=BASE_URL, timeout=300)
    return (e2e,)


@app.cell
def _():
    config = "api_simulation_default.json"
    num_generations = 8
    num_seeds = 4
    experiment_id = "cd1_demo_notebook_test_0"
    description = experiment_id.replace("_", " ")
    return config, description, experiment_id, num_generations, num_seeds


@app.cell
def _():
    import marimo as mo

    get_simulator, set_simulator = mo.state(None)
    get_simulation, set_simulation = mo.state(None)
    get_simulation_status, set_simulation_status = mo.state("pending")

    simulator_button = mo.ui.run_button(kind="warn", label="Prepare Simulator")
    simulation_button = mo.ui.run_button(kind="success", label="Run Simulation Workflow")
    simulation_status_button = mo.ui.run_button(kind="success", label="Get Simulation Status")
    return (
        get_simulation,
        get_simulator,
        mo,
        set_simulation,
        set_simulation_status,
        set_simulator,
        simulation_button,
        simulation_status_button,
        simulator_button,
    )


@app.cell
def _(
    config,
    description,
    e2e,
    experiment_id,
    get_simulator,
    num_generations,
    num_seeds,
    set_simulation,
    set_simulation_status,
    set_simulator,
    simulation_button,
    simulation_status_button,
    simulator_button,
):
    if simulator_button.value:
        simulator = e2e.get_simulator()
        set_simulator(simulator)

    if simulation_button.value:
        simulator = get_simulator()
        simulation = e2e.run_workflow(
            experiment_id=experiment_id,
            simulator_id=simulator.database_id,
            num_generations=num_generations,
            config_filename=config,
            num_seeds=num_seeds,
            description=description,
        )
        set_simulation(simulation)

    if simulation_status_button.value:
        status = e2e.get_workflow_status(simulation.database_id)
        set_simulation_status(status)
    return


@app.cell
def _(mo, simulation_button, simulation_status_button, simulator_button):
    mo.vstack([simulator_button, mo.hstack([simulation_button, simulation_status_button], justify="start")])
    return


@app.cell
def _(get_simulator):
    get_simulator()
    return


@app.cell
def _(get_simulation):
    get_simulation()
    return


@app.cell
def _(e2e):
    outputs = e2e.get_output_data(simulation_id=61)
    return (outputs,)


@app.cell
def _(TsvOutputFile):
    from io import StringIO

    import polars as pl

    def read_output(output: TsvOutputFile):
        return pl.read_csv(StringIO(output.content), separator="\t")

    def plot_output(df: pl.DataFrame, x: str, y: str) -> None:
        return df.plot.line(x=x, y=y)

    return plot_output, read_output


@app.cell
def _(outputs, read_output):
    output_i = outputs[0]
    df_i = read_output(output_i)
    df_i  # noqa: B018
    return (df_i,)


@app.cell
def _(df_i, plot_output):
    plot_output(df_i, x="std", y="mean")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
