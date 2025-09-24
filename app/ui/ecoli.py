import marimo

__generated_with = "0.14.17"
app = marimo.App(width="full")


@app.cell
def _():
    from enum import StrEnum
    from dataclasses import dataclass, field
    from typing import Any
    from pprint import pp

    from libsms import Client, models, api
    from libsms.api import sms_api

    from libsms.models.experiment_analysis_request import ExperimentAnalysisRequest
    from libsms.models.experiment_analysis_dto import ExperimentAnalysisDTO
    from libsms.models.experiment_request import ExperimentRequest
    from libsms.models.experiment_metadata import ExperimentMetadata
    from libsms.models.ecoli_simulation_dto import EcoliSimulationDTO

    from pathlib import Path

    class Apis:
        simulate = [
            fp.parts[-1].replace(".py", "")
            for fp in (Path(api.__file__).parent / "simulations").iterdir()
            if "__init__" not in str(fp)
        ]
        analyze = [
            fp.parts[-1].replace(".py", "")
            for fp in (Path(api.__file__).parent / "analyses").iterdir()
            if "__init__" not in str(fp)
        ]

    @dataclass
    class FlexData:
        _data: dict[str, Any] = field(default_factory=dict)

        def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            self._data = kwargs

        def __getattr__(self, item):  # type: ignore[no-untyped-def]
            return self._data[item]

        def __getitem__(self, item):  # type: ignore[no-untyped-def]
            return self._data[item]

        def keys(self):  # type: ignore[no-untyped-def]
            return self._data.keys()

        def dict(self) -> dict[str, Any]:
            return self._data

    class BaseUrl(StrEnum):
        LOCAL = "http://localhost:8888"
        PRODUCTION = "https://sms.cam.uchc.edu"

    class DataService:
        def __init__(self, local: bool = True):
            self.local = local

        async def fetch(self, fetch_module, *args, **kwargs):
            async with Client(base_url=BaseUrl.LOCAL if self.local else BaseUrl.PRODUCTION) as client:
                func = fetch_module.asyncio_detailed
                resp = await func(*args, **kwargs, client=client)
                return resp.parsed.additional_properties

        async def ping(self):
            return await self.fetch(fetch_module=sms_api.check_health_health_get)

    return (
        Apis,
        BaseUrl,
        Client,
        EcoliSimulationDTO,
        ExperimentMetadata,
        ExperimentRequest,
        models,
        pp,
    )


@app.cell
def _(Apis):
    Apis.simulate
    return


@app.cell
def _():
    """
    run simulation:
    ===============
    ExperimentRequest, ExperimentMetadata -> EcoliSimulationDTO

    run analysis:
    =============
    ExperimentAnalysisRequest -> ExperimentAnalysisDTO
    """
    return


@app.cell
def _():
    import marimo as mo

    get_simulation, set_simulation = mo.state(None)
    get_simstatus, set_simstatus = mo.state(None)
    get_simlog, set_simlog = mo.state(None)
    return (
        get_simlog,
        get_simstatus,
        get_simulation,
        mo,
        set_simlog,
        set_simstatus,
        set_simulation,
    )


@app.cell
async def _(
    BaseUrl,
    Client,
    ExperimentMetadata,
    ExperimentRequest,
    models,
    pp,
    set_simulation,
):
    from libsms.api.simulations import run_ecoli_simulation
    from libsms.models import BodyRunEcoliSimulation

    def experiment_metadata(**fields):
        metadata = ExperimentMetadata()
        metadata.additional_properties.update(fields)
        return metadata

    async def launch_simulation(parameters: ExperimentRequest, metadata: ExperimentMetadata, local: bool = False):
        """ExperimentRequest, ExperimentMetadata -> EcoliSimulationDTO"""
        async with Client(base_url=BaseUrl.LOCAL if local else BaseUrl.PRODUCTION) as client:
            resp: models.Response = await run_ecoli_simulation.asyncio_detailed(
                client=client, body=BodyRunEcoliSimulation(request=parameters, metadata=metadata)
            )
            return resp.parsed

    experiment_id = "client_sim_test_0"
    simname = experiment_id
    parameters = ExperimentRequest(experiment_id=experiment_id, simulation_name=simname)
    metadata = experiment_metadata(context="client_ui_test")
    simulation = await launch_simulation(parameters=parameters, metadata=metadata, local=True)
    set_simulation(simulation)
    pp(simulation)
    return (simulation,)


@app.cell
async def _(
    BaseUrl,
    Client,
    EcoliSimulationDTO,
    get_simulation,
    models,
    pp,
    set_simstatus,
    simulation,
):
    from libsms.api.simulations import get_ecoli_simulation_status

    async def get_simulation_status(simulation: EcoliSimulationDTO, local: bool = True):
        """ExperimentRequest, ExperimentMetadata -> EcoliSimulationDTO"""
        async with Client(base_url=BaseUrl.LOCAL if local else BaseUrl.PRODUCTION) as client:
            resp: models.Response = await get_ecoli_simulation_status.asyncio_detailed(
                client=client, id=simulation.database_id
            )
            return resp.parsed

    if get_simulation() is not None:
        simulation_status = await get_simulation_status(simulation=simulation, local=True)
        set_simstatus(simulation_status)
        pp(simulation_status)
    return


@app.cell
async def _(
    BaseUrl,
    Client,
    EcoliSimulationDTO,
    get_simulation,
    models,
    pp,
    set_simlog,
    simulation,
):
    from libsms.api.simulations import get_ecoli_simulation_log

    async def get_simulation_log(simulation: EcoliSimulationDTO, local: bool = True):
        """ExperimentRequest, ExperimentMetadata -> EcoliSimulationDTO"""
        async with Client(base_url=BaseUrl.LOCAL if local else BaseUrl.PRODUCTION) as client:
            resp: models.Response = await get_ecoli_simulation_log.asyncio_detailed(
                client=client, id=simulation.database_id
            )
            return resp.parsed

    if get_simulation() is not None:
        simulation_log = await get_simulation_log(simulation=simulation, local=True)
        set_simlog(simulation_log)
        pp(simulation_log)
    return


@app.cell
def _(get_simlog, get_simstatus, get_simulation, mo):
    tabnames = ["simulation", "status", "log"]
    getters = [get_simulation, get_simstatus, get_simlog]

    mo.ui.tabs({
        "simulation": mo.json(get_simulation().to_dict()),
        "status": mo.ui.text_area(value=get_simstatus().status, disabled=True).callout(kind="success"),
        "log": get_simlog(),
    })
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
