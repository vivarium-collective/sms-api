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
    # create service with registerable callbacks
    # this service provides the data as needed specifically by the notebooks
    # have listeners for the registered callbacks

    import os
    import json
    import asyncio
    import time
    import logging
    from pprint import pp, pformat
    from pathlib import Path
    from contextlib import contextmanager
    from enum import StrEnum
    from typing import Generator

    import marimo as mo
    import polars as pl
    import altair as alt
    from altair import Chart
    from fastapi import HTTPException
    from httpx import AsyncClient, QueryParams, Client, HTTPStatusError, Timeout

    from sms_api.simulation.models import (
        SimulatorVersion,
        EcoliSimulationRequest,
        EcoliExperiment,
        WorkerEvent,
        ParcaDataset,
        BaseModel,
        JobStatus
    )
    from sms_api.config import get_settings
    from app.api.simulations import EcoliSim
    from app.api.client_wrapper import ClientWrapper


    logger = logging.getLogger(__file__)

    def display_dto(dto: BaseModel | None = None) -> mo.Html | None:
        from pprint import pformat
        if not dto:
            return None
        return mo.md(f"```python\n{pformat(dto.dict())}\n```")
    return (
        Client,
        EcoliExperiment,
        EcoliSimulationRequest,
        Generator,
        HTTPStatusError,
        JobStatus,
        ParcaDataset,
        StrEnum,
        Timeout,
        WorkerEvent,
        alt,
        asyncio,
        contextmanager,
        display_dto,
        get_settings,
        mo,
        pformat,
        pl,
        time,
    )


@app.cell
def _(Client, Generator, StrEnum, Timeout, contextmanager, get_settings):
    # -- api client and call setup -- #

    SIMULATION_TEST_ID = 3

    def get_base_url() -> str:
        settings = get_settings()
        api_server_url = settings.marimo_api_server
        if not len(api_server_url):
            api_server_url = "http://localhost:8000"
        return f"{api_server_url}/core"


    @contextmanager
    def api_client(base_url: str | None = None, timeout: int | None = None) -> Generator[Client, None, None]:
        """
        example usage:
        python```
            with api_client() as client:
                url = format_endpoint_url(ApiResource.SIMULATOR, 'versions')
                resp = client.get(url=url)
                print(resp.json())
        ```
        """
        with Client(
            base_url=base_url or get_base_url(),
            timeout=Timeout(timeout or 22.0)
        ) as client:
            yield client


    class ApiResource(StrEnum):
        SIMULATOR = "simulator"
        SIMULATION = "simulation"


    def format_endpoint_url(resource: ApiResource, *subpaths):
        base_url = get_base_url()
        return f"{base_url}/{resource}/{'/'.join(list(subpaths))}"

    # client = ClientWrapper(base_url=base_url)
    return ApiResource, api_client, format_endpoint_url


@app.cell
def _(WorkerEvent, alt, mo, pl):
    # -- marimo-specific plot setup and mass listener data selection -- #

    COLORS = [
        "#1f77b4",  # blue
        "#ff7f0e",  # orange
        "#2ca02c",  # green
        "#d62728",  # red
        "#9467bd",  # purple
        "#8c564b",  # brown
        "#e377c2",  # pink
    ]

    MASS_COLUMNS = {
        "Protein": "listeners__mass__protein_mass",
        "tRNA": "listeners__mass__tRna_mass",
        "rRNA": "listeners__mass__rRna_mass",
        "mRNA": "listeners__mass__mRna_mass",
        "DNA": "listeners__mass__dna_mass",
        "Small Mol.s": "listeners__mass__smallMolecule_mass",
        "Dry": "listeners__mass__dry_mass",
        "Time": "time",
    }

    MAPPING = {column_name: column_name.split("__")[-1] for column_name in MASS_COLUMNS.values()}


    def select_keys(
        data: dict[str, int | float | list[int] | dict[str, float]], keys: list[str]
    ) -> dict[str, int | float | list[int] | dict[str, float]]:
        return {key: data.get(key) for key in keys if key in data}

    def get_events_dataframe(events: list[WorkerEvent] | None = None) -> pl.DataFrame:
        if events:
            dataframes = []
            for event in events:
                event_data = event.model_dump()
                selected_keys = select_keys(event_data["mass"], list(MAPPING.values()))
                # selected_keys['time'] = event.time
                df_event = pl.DataFrame({key: event.mass[key] for key in selected_keys})
                df_event = df_event.with_columns(pl.lit(event.time).alias("time"))
                dataframes.append(df_event)
            return pl.concat(dataframes, how="vertical_relaxed").sort("time")
        return pl.DataFrame()

    def plot_mass_fractions_from_worker_events(df: pl.DataFrame | None = None) -> mo.ui.altair_chart | None:
        """Plot normalized biomass component mass fractions from a list of Polars DataFrames."""
        if df.is_empty():
            return None
        # Concatenate all simulation results
        mass_data = df
        # Assumes single-cell data
        mass_columns = {
            "Protein": "protein_mass",
            "tRNA": "tRna_mass",
            "rRNA": "rRna_mass",
            "mRNA": "mRna_mass",
            "DNA": "dna_mass",
            "Small Mol": "smallMolecule_mass",
            "Dry": "dry_mass",
        }
        # Compute average mass fractions
        fractions = {k: (mass_data[v] / mass_data["dry_mass"]).mean() for k, v in mass_columns.items()}
        # Build new normalized dataframe
        new_columns = {
            # "Time (min)": (mass_data["time"] - mass_data["time"].min()) / 60,
            "Time (min)": (mass_data["time"] - mass_data["time"].min()) / 60,
            **{f"{k} ({fractions[k]:.3f})": mass_data[v] / mass_data[v][0] for k, v in mass_columns.items()},  # type: ignore[str-bytes-safe]
        }
        mass_fold_change_df = pl.DataFrame(new_columns)
        # Melt for Altair plotting
        melted_df = mass_fold_change_df.melt(
            id_vars="Time (min)",
            variable_name="Submass",
            value_name="Mass (normalized by t = 0 min)",
        )
        title = "Biomass components (average fraction of total dry mass)"
        chart: alt.Chart = mo.ui.altair_chart(
            alt.Chart(melted_df)
            .transform_calculate(SubmassName="substring(datum.Submass, 0, indexof(datum.Submass, ' ('))")
            .mark_line()
            .encode(
                x=alt.X("Time (min):Q", title="Time (min)"),
                y=alt.Y("Mass (normalized by t = 0 min):Q"),
                color=alt.Color("SubmassName:N", scale=alt.Scale(range=COLORS), legend=alt.Legend(labelFontSize=14)),
            )
            .properties(title=title)
        )
        return chart
    return get_events_dataframe, plot_mass_fractions_from_worker_events


@app.cell
def _(
    ApiResource,
    EcoliExperiment,
    EcoliSimulationRequest,
    HTTPStatusError,
    ParcaDataset,
    WorkerEvent,
    api_client,
    format_endpoint_url,
    mo,
):
    # -- client calls to the API, returning the appropriate DTOs (all with the 'on_' prefix) -- #
    @mo.cache
    def on_get_parcas() -> list[ParcaDataset]:
        try:
            with api_client() as client:
                url = format_endpoint_url(ApiResource.SIMULATION, 'parca', 'versions')
                resp = client.get(url=url)
                resp.raise_for_status()
                return [ParcaDataset(**dataset) for dataset in resp.json()]
        except HTTPStatusError as e:
            raise HTTPStatusError(message=str(e))

    def on_run_simulation(request: EcoliSimulationRequest) -> EcoliExperiment:
        try:
            with api_client() as client:
                url = format_endpoint_url(ApiResource.SIMULATION, 'run')
                request_payload = request.as_payload().dict()
                resp = client.post(url=url, json=request_payload)
                resp.raise_for_status()
                return EcoliExperiment(**resp.json())
        except HTTPStatusError as e:
            raise HTTPStatusError(message=str(e))

    def on_get_worker_events(simulation_id: int) -> list[WorkerEvent]:
        try:
            with api_client() as client:
                url = format_endpoint_url(ApiResource.SIMULATION, 'run', 'events')
                resp = client.get(url=url, params={"simulation_id": simulation_id})
                resp.raise_for_status()
                return [WorkerEvent(**event) for event in resp.json()]
        except HTTPStatusError as e:
            raise HTTPStatusError(message=str(e))

    def on_get_simulation_status(simulation_id: int) -> str:
        with api_client() as client:
            try:
                url = format_endpoint_url(ApiResource.SIMULATION, 'run', 'status')
                resp = client.get(url=url, params={"simulation_id": simulation_id})
                status = resp.json()['status']
                return status
            except HTTPStatusError as e:
                raise HTTPStatusError(message=str(e))

    try:
        parca_datasets = on_get_parcas()
    except ValueError as e:
        print(e)
        parca_datasets = None
    return (
        on_get_simulation_status,
        on_get_worker_events,
        on_run_simulation,
        parca_datasets,
    )


@app.cell
def _(EcoliSimulationRequest, ParcaDataset, parca_datasets):
    # build the request

    def extract_simulation_request(
        parca_datasets: list[ParcaDataset],
        variant_config: dict[str, dict[str, float]] | None = None  # TODO: formalize this
    ) -> EcoliSimulationRequest:
        if not len(parca_datasets):
            raise ValueError('There are no datasets uploaded')
        active_parca_dataset: ParcaDataset = parca_datasets[-1]
        return EcoliSimulationRequest(
            parca_dataset_id=active_parca_dataset.database_id,
            simulator=active_parca_dataset.parca_dataset_request.simulator_version,
            variant_config=variant_config or {"named_parameters": {"param1": 0.5, "param2": 0.5}}
        )

    request: EcoliSimulationRequest = extract_simulation_request(parca_datasets)
    return (request,)


@app.cell
def _(JobStatus, alt, mo, pl):
    # set mutable state attributes (hooks, really)
    get_dataframes, set_dataframes = mo.state([])
    get_current_index, set_current_index = mo.state(0)
    get_is_polling, set_is_polling = mo.state(False)
    get_chart, set_chart = mo.state(mo.ui.altair_chart(alt.Chart().mark_line().encode()))
    get_status, set_status = mo.state(JobStatus.WAITING)
    get_events, set_events = mo.state([])
    get_events_df, set_events_df = mo.state(pl.DataFrame())
    get_simulation_id, set_simulation_id = mo.state(None)

    # iteratively slice the events df by 10 TODO: is this needed anymore?
    step_size = 10
    return (
        get_chart,
        get_current_index,
        get_dataframes,
        get_events,
        get_events_df,
        get_is_polling,
        get_simulation_id,
        get_status,
        set_chart,
        set_current_index,
        set_dataframes,
        set_events,
        set_events_df,
        set_is_polling,
        set_simulation_id,
        set_status,
        step_size,
    )


@app.cell
def _(mo):
    # set and display run button
    run_simulation_button = mo.ui.run_button(label=f"{mo.icon('eos-icons:genomic')} Run Simulation {mo.icon('svg-spinners:blocks-wave')}", kind="success")
    return (run_simulation_button,)


@app.cell
async def _(
    EcoliExperiment,
    asyncio,
    on_run_simulation,
    request: "EcoliSimulationRequest",
    run_simulation_button,
    set_is_polling,
):
    # run the simulation
    experiment: EcoliExperiment | None = None  # on_run_simulation()
    if run_simulation_button.value:
        experiment = on_run_simulation(request)
        await asyncio.sleep(0.45)
        # set polling
        set_is_polling(True)
    return (experiment,)


@app.cell
def _(
    EcoliExperiment,
    experiment: "EcoliExperiment | None",
    set_simulation_id,
):
    # get simulation id
    def fetch_simulation_id(experiment: EcoliExperiment | None = None) -> int | None:
        return experiment.simulation.database_id if experiment else None

    current_simulation_id = fetch_simulation_id(experiment)
    if current_simulation_id is not None:
        set_simulation_id(current_simulation_id)
    return


@app.cell
def _(
    WorkerEvent,
    get_events,
    get_simulation_id,
    on_get_worker_events,
    set_events,
):
    latest_events = get_events()
    simulation_id = get_simulation_id()
    if not len(latest_events) and simulation_id is not None:
        latest_events: list[WorkerEvent] = on_get_worker_events(simulation_id)
        set_events(latest_events)
    return (simulation_id,)


@app.cell
def _(get_events, get_events_dataframe, set_events_df):
    current_events = get_events()
    latest_events_df = get_events_dataframe(current_events)
    set_events_df(latest_events_df)
    return


@app.cell
def _(
    JobStatus,
    get_current_index,
    get_dataframes,
    get_events_dataframe,
    get_events_df,
    get_is_polling,
    get_status,
    on_get_simulation_status,
    on_get_worker_events,
    pl,
    plot_mass_fractions_from_worker_events,
    set_chart,
    set_current_index,
    set_dataframes,
    set_events,
    set_events_df,
    set_status,
    simulation_id,
    step_size,
    time,
):
    def update_data_index():
        next_index = get_current_index()
        simulation_events_df = get_events_df()
        end_index = min(next_index + step_size, simulation_events_df.height)
        if next_index < simulation_events_df.height:
            updated_dataframes = get_dataframes()
            updated_dataframes.append(simulation_events_df.slice(next_index, end_index - next_index))
            set_dataframes(updated_dataframes)
            set_current_index(end_index)

    def render_chart():
        current_dataframes = get_dataframes()
        combined_df = get_events_df()
        if len(current_dataframes):
            combined_df = pl.concat(current_dataframes)
        chart = plot_mass_fractions_from_worker_events(combined_df)
        # return mo.vstack([plt_button, mo.md("Press the button to start polling and plotting.")])
        return chart

    def on_poll(buffer: float | None = None):
        # if polling is turned on, get latest event data
        if get_is_polling():
            # small buffer -- let it breathe!
            time.sleep(buffer or 1.1)
            # get latest status to make sure its still running
            latest_status = on_get_simulation_status(simulation_id=simulation_id)
            if get_status() == JobStatus.FAILED:
                raise ValueError("The job has failed.")
            else:
                # if it's running, set the latest status
                set_status(latest_status)
            worker_events = on_get_worker_events(simulation_id)
            simulation_events_df = get_events_dataframe(worker_events)

            # set latest event data (TODO: what's the endpoint?)
            set_events(worker_events)
            set_events_df(simulation_events_df)
            update_data_index()

            set_chart(render_chart())

            # bitflip polling
            # set_is_polling(False)
        else:
            print(f'Not polling')
    return (on_poll,)


@app.cell
def _(
    display_dto,
    experiment: "EcoliExperiment | None",
    get_chart,
    get_is_polling,
    mo,
    on_poll,
    run_simulation_button,
    set_chart,
):
    # set latest render
    latest_chart = get_chart()
    set_chart(latest_chart)

    refresh = None
    if get_is_polling():
        refresh = mo.ui.refresh(label="Refreshing data...", default_interval=1, on_change=lambda _: on_poll())

    # ui stack with run button and latest render
    stack_items = [run_simulation_button, display_dto(experiment), latest_chart]
    if refresh is not None:
        stack_items.append(refresh)
    return (stack_items,)


@app.cell
def _(mo, stack_items):
    mo.vstack(stack_items)
    return


@app.cell
def _():
    # worker_events: list[WorkerEvent] = on_get_worker_events(simulation_id)
    #
    # # get initial events dataframe TODO: we must ensure that this is always the freshest call
    # simulation_events_df = get_events_dataframe(worker_events)
    #
    # def set_step_index(worker_events: list[WorkerEvent], simulation_events_df: pl.DataFrame) -> None:
    #     if len(worker_events):
    #         next_index = mo.state.current_index
    #         end_index = min(next_index + step_size, simulation_events_df.height)
    #         if next_index < simulation_events_df.height:
    #             mo.state.dataframes.append(simulation_events_df.slice(next_index, end_index - next_index))
    #             mo.state.current_index = end_index
    #     return None
    #
    # async def poll_events(buffer: float = 1.8) -> list[WorkerEvent]:
    #     await asyncio.sleep(buffer)
    #     return on_get_worker_events(simulation_id)
    #
    # def log_events(status, iteration, worker_events) -> None:
    #     print(f'Status:\n  {status}\nIteration:\n  {iteration}\nEvents:\n')
    #     pp(worker_events)
    #     print(f'---\n')
    #
    # # set initial step index
    # set_step_index(worker_events, simulation_events_df)
    #
    # # main polling
    # if experiment is not None:
    #     buffer = 1.1
    #     max_timeout = 50
    #     iteration = 0
    #     status = JobStatus.WAITING
    #
    #     # get status
    #     while not status == JobStatus.COMPLETED and iteration < max_timeout:
    #         try:
    #             status = on_get_simulation_status(simulation_id=simulation_id)
    #         except:
    #             print(f'Could not get status for iteration: {iteration}')
    #             iteration += 1
    #             continue
    #
    #         # update data and step index
    #         worker_events = await poll_events()
    #         simulation_events_df = get_events_dataframe(worker_events)
    #         set_step_index(worker_events, simulation_events_df)
    #
    #         # increment timer
    #         iteration += 1
    #
    #         # logging
    #         if not len(worker_events):
    #             print(f'No events at iteration: {iteration}\nStatus: {status}\n---')
    #         else:
    #             log_events(status, iteration, worker_events)
    #
    #
    #         await asyncio.sleep(buffer)
    return


@app.cell
def _():
    # compile dataframe of all current events
    # simulation_events_df = get_events_dataframe(worker_events)
    return


@app.cell
def _():
    # if not hasattr(mo.state, "dataframes"):
    #     mo.state.dataframes = []
    # if not hasattr(mo.state, "current_index"):
    #     mo.state.current_index = 0
    #
    # step_size = 10  # number of rows to append per button press
    # plt_button = mo.ui.run_button(label=f"{mo.icon('svg-spinners:blocks-wave')} Plot Mass Fractions", kind="danger")
    return


@app.cell
def _():
    # if plt_button.value:
    #     next_index = mo.state.current_index
    #     end_index = min(next_index + step_size, simulation_events_df.height)
    #     if next_index < simulation_events_df.height:
    #         mo.state.dataframes.append(simulation_events_df.slice(next_index, end_index - next_index))
    #         mo.state.current_index = end_index
    #
    # # Display chart
    # def display_chart():
    #     if mo.state.dataframes:
    #         combined_df = pl.concat(mo.state.dataframes)
    #         chart = plot_mass_fractions_from_worker_events(combined_df)
    #         return mo.vstack([plt_button, chart])
    #     else:
    #         return mo.vstack([plt_button, mo.md("Press the button to start streaming.")])
    #
    # display_chart()
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _():
    return


@app.cell
def _(mo):
    mo.md(r"""#### Get status for any simulation""")
    return


@app.cell
def _(mo):
    get_status_header = mo.md(f"### Get Simulation Status")
    form = mo.ui.text_area(placeholder="Enter simulation id", full_width=False).form()
    mo.vstack([get_status_header, form])
    return (form,)


@app.cell
def _(form, mo, on_get_simulation_status, pformat):
    requested_sim_status = None
    sim_id = None
    if form.value is not None:
        sim_id = int(form.value)
        requested_sim_status = on_get_simulation_status(simulation_id=sim_id)
    mo.md(f"""
    ### Status for Simulation ID: `{sim_id}`

    ```python
    {pformat(requested_sim_status)}
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""### Get an array of events for any simulation""")
    return


@app.cell
def _(mo):
    get_events_header = mo.md(f"### Get Simulation Events")
    events_form = mo.ui.text_area(placeholder="Enter simulation id", full_width=False).form()
    mo.vstack([get_events_header, events_form])
    return (events_form,)


@app.cell
def _(events_form, mo, on_get_worker_events, pformat):
    requested_sim_events = None
    sim_id_ = None
    if events_form.value is not None:
        sim_id_ = int(events_form.value)
        requested_sim_events = on_get_worker_events(simulation_id=sim_id_)
    mo.md(f"""
    ### Events for Simulation ID: `{sim_id_}`

    ```python
    {pformat(requested_sim_events)}
    ```
    """)
    return


@app.cell
def _():
    return


@app.cell
def _():
    # get_events_button = mo.ui.run_button(label="Get Simulation Events")
    # get_events_button
    return


@app.cell
def _():
    # worker_events: list[WorkerEvent] = on_get_worker_events(simulation_id)
    #
    # async def poll_events(buffer: float = 1.8) -> list[WorkerEvent]:
    #     await asyncio.sleep(buffer)
    #     return on_get_worker_events(simulation_id)
    #
    # def log_events(status, iteration, worker_events) -> None:
    #     print(f'Status:\n  {status}\nIteration:\n  {iteration}\nEvents:\n')
    #     pp(worker_events)
    #     print(f'---\n')
    #
    # def display_chart(plt_button) -> mo.Html:
    #     if mo.state.dataframes:
    #         combined_df = pl.concat(mo.state.dataframes)
    #         chart = plot_mass_fractions_from_worker_events(combined_df)
    #         return mo.vstack([plt_button, chart])
    #     else:
    #         return mo.vstack([plt_button, mo.md("Press the button to start streaming.")])
    #
    # expected_times_fp = Path(os.path.dirname(__file__)).parent.parent / "assets/expected_times.json"
    # if experiment is not None:
    #     max_duration = 20
    #     iteration = 0
    #     status = "waiting"
    #     with open(str(expected_times_fp), 'r') as fp:
    #         expected_times = json.load(fp)
    #     for iteration in mo.status.progress_bar(
    #         expected_times,
    #         title="Loading",
    #         subtitle="Please wait",
    #         show_eta=True,
    #         show_rate=True
    #     ):
    #         # get status
    #         with api_client() as client:
    #             try:
    #                 url = format_endpoint_url(ApiResource.SIMULATION, 'run', 'status')
    #                 resp = client.get(url=url, params={"simulation_id": simulation_id})
    #                 status = resp.json()['status']
    #                 if status == "completed":
    #                     print(f"Simulation Complete at iteration: {iteration}!\n")
    #                     break
    #             except:
    #                 print(f'Could not get status for iteration: {iteration}')
    #                 continue
    #         worker_events = await poll_events()
    #         if len(worker_events):
    #             log_events(status, iteration, worker_events)
    #
    #         else:
    #             print(f'No events\nStatus: {status}\n---')
    #         display_chart(plt_button)
    #         await asyncio.sleep(1.0)

    ############original###################
    # if get_events_button.value:
    #     max_duration = 20
    #     iteration = 0
    #     status = "waiting"
    #     for _ in mo.status.progress_bar(
    #         range(max_duration),
    #         title="Loading",
    #         subtitle="Please wait",
    #         show_eta=True,
    #         show_rate=True
    #     ):
    #         while iteration < max_duration:
    #             # get status
    #             with api_client() as client:
    #                 try:
    #                     url = format_endpoint_url(ApiResource.SIMULATION, 'run', 'status')
    #                     resp = client.get(url=url, params={"simulation_id": simulation_id})
    #                     status = resp.json()['status']
    #                 except:
    #                     print(f'Could not get status for iteration: {iteration}')
    #                     iteration += 1
    #                     continue
    #             worker_events = await poll_events()
    #             if len(worker_events):
    #                 log_events(status, iteration, worker_events)
    #             else:
    #                 print(f'Status: {status}\n---')
    #             iteration += 1
    #             time.sleep(1.0)
    #######################################

    # simulation_events_df = get_events_dataframe(worker_events)
    #
    # if not hasattr(mo.state, "dataframes"):
    #     mo.state.dataframes = []
    # if not hasattr(mo.state, "current_index"):
    #     mo.state.current_index = 0
    #
    # step_size = 10  # number of rows to append per button press
    #
    # if len(worker_events):
    #     next_index = mo.state.current_index
    #     end_index = min(next_index + step_size, simulation_events_df.height)
    #     if next_index < simulation_events_df.height:
    #         mo.state.dataframes.append(simulation_events_df.slice(next_index, end_index - next_index))
    #         mo.state.current_index = end_index
    return


if __name__ == "__main__":
    app.run()
