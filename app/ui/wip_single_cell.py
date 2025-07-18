import marimo

__generated_with = "0.14.11"
app = marimo.App(
    width="medium",
    app_title="Atlantis - Single Cell",
    layout_file="layouts/wip_single_cell.grid.json",
)


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

    import numpy as np
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
        Path,
        StrEnum,
        Timeout,
        WorkerEvent,
        alt,
        asyncio,
        contextmanager,
        get_settings,
        mo,
        os,
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
            "Protein": "listeners__mass__protein_mass",
            "tRNA": "listeners__mass__tRna_mass",
            "rRNA": "listeners__mass__rRna_mass",
            "mRNA": "listeners__mass__mRna_mass",
            "DNA": "listeners__mass__dna_mass",
            "Small Mol.s": "listeners__mass__smallMolecule_mass",
            "Dry": "listeners__mass__dry_mass"
        }
        # Compute average mass fractions
        fractions = {k: (mass_data[v] / mass_data["listeners__mass__dry_mass"]).mean() for k, v in mass_columns.items()}
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
            value_name="Normalized Mass",
        )
        title = "Biomass components (average fraction of total dry mass)"
        chart: alt.Chart = mo.ui.altair_chart(
            alt.Chart(melted_df)
            .transform_calculate(SubmassName="substring(datum.Submass, 0, indexof(datum.Submass, ' ('))")
            .mark_line()
            .encode(
                x=alt.X("Time (min):Q", title="Time (min)"),
                y=alt.Y("Normalized Mass:Q"),
                color=alt.Color("SubmassName:N", scale=alt.Scale(range=COLORS), legend=alt.Legend(labelFontSize=14)),
            )
            .properties(title=title),
            chart_selection=True,
            legend_selection=True
        )
        return chart
    return (
        MASS_COLUMNS,
        get_events_dataframe,
        plot_mass_fractions_from_worker_events,
    )


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

    # try:
    #     parca_datasets = on_get_parcas()
    # except ValueError as e:
    #     print(e)
    #     parca_datasets = None
    return on_get_simulation_status, on_get_worker_events, on_run_simulation


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
    get_is_running, set_is_running = mo.state(False)

    # iteratively slice the events df by 10 TODO: is this needed anymore?
    step_size = 10
    return (
        get_current_index,
        get_dataframes,
        get_events,
        get_events_df,
        get_is_polling,
        get_simulation_id,
        get_status,
        set_current_index,
        set_dataframes,
        set_events,
        set_events_df,
        set_is_polling,
        set_is_running,
        set_simulation_id,
        set_status,
        step_size,
    )


@app.cell
def _(set_is_polling, set_is_running):
    def on_stop():
        set_is_polling(False)
        set_is_running(False)
    return (on_stop,)


@app.cell
def _(mo, on_stop):
    # set and display run button
    run_simulation_button = mo.ui.run_button(label=f"{mo.icon('eos-icons:genomic')} Run Simulation", kind="success")
    pause_simulation_button = mo.ui.run_button(label=f"{mo.icon('formkit:pause', size=16, inline=False)}", kind="warn")
    stop_simulation_button = mo.ui.run_button(label=f"{mo.icon('formkit:stop', size=16, inline=False)}", kind="danger", on_change=lambda _: on_stop())
    return (
        pause_simulation_button,
        run_simulation_button,
        stop_simulation_button,
    )


@app.cell
async def _(
    EcoliExperiment,
    asyncio,
    on_run_simulation,
    request: "EcoliSimulationRequest",
    run_simulation_button,
    set_is_polling,
    set_is_running,
):
    # run the simulation
    experiment: EcoliExperiment | None = None  # on_run_simulation()
    if run_simulation_button.value:
        set_is_running(True)
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


@app.class_definition
class FailedJobError(Exception):
    pass


@app.cell
def _(
    JobStatus,
    get_current_index,
    get_dataframes,
    get_events_dataframe,
    get_events_df,
    get_is_polling,
    on_get_simulation_status,
    on_get_worker_events,
    pl,
    plot_mass_fractions_from_worker_events,
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
        print(f'got combined df: {combined_df}')
        return chart

    def on_poll(buffer: float | None = None):
        try:
            # if polling is turned on, get latest event data
            if get_is_polling():
                # small buffer -- let it breathe!
                time.sleep(buffer or 1.1)
                # get latest status to make sure its still running
                latest_status = on_get_simulation_status(simulation_id=simulation_id)
                if latest_status == JobStatus.FAILED:
                    raise FailedJobError("The job has failed.")
                elif latest_status == JobStatus.COMPLETED:
                    print('Simulation has completed.')
                    set_status(latest_status)
                    return

                set_status(latest_status)

                worker_events = on_get_worker_events(simulation_id)
                simulation_events_df = get_events_dataframe(worker_events)

                # set latest event data (TODO: what's the endpoint?)
                set_events(worker_events)
                set_events_df(simulation_events_df)
                # update_data_index()

                # set_chart(render_chart())

                # bitflip polling
                # set_is_polling(False)
            else:
                print(f'Not polling')
        except FailedJobError as e:
            raise FailedJobError(e)

    return on_poll, render_chart


@app.cell
def _(
    JobStatus,
    get_is_polling,
    get_status,
    mo,
    on_poll,
    pause_simulation_button,
    run_simulation_button,
    set_is_polling,
    set_is_running,
    stop_simulation_button,
):
    latest_status = get_status()
    if latest_status == JobStatus.FAILED or latest_status == JobStatus.COMPLETED:
        print('Stopping simulation')
        # refresh = None
        set_is_polling(False)
        set_is_running(False)

    refresh = None
    if get_is_polling():
        refresh = mo.ui.refresh(
            label="Refreshing data...",
            options=[0.25, 0.5, 1.0, 5.0, 10.0],
            default_interval=0.25,
            on_change=lambda _: on_poll()
        )

    # ui stack with run button and latest render
    hstack_items = [run_simulation_button, pause_simulation_button, stop_simulation_button]
    if refresh is not None:
        hstack_items.append(refresh)
    button_hstack = mo.hstack(hstack_items, justify="start")
    return (button_hstack,)


@app.cell
def _(button_hstack):
    button_hstack
    return


@app.cell
def _(render_chart):
    # set latest render
    latest_chart = render_chart()
    latest_chart
    return


@app.cell
def _(get_events_df, mo):
    mo.accordion({
        "Explore Data": mo.ui.data_explorer(get_events_df())
    })
    return


@app.cell
def _(Path, os):
    outdir = Path('assets/tests/test_history/')
    pqpaths = iter([outdir / fname for fname in os.listdir(outdir)])
    return (pqpaths,)


@app.cell
def _(MASS_COLUMNS, mo, pl):
    getPolling, setPolling = mo.state(None)
    getRowIndex, setRowIndex = mo.state(1)
    getFrames, setFrames = mo.state([])
    getDf, setDf = mo.state(pl.DataFrame(
                dict(zip(
                    list(MASS_COLUMNS.values()),
                    [1.0 for _ in MASS_COLUMNS]
                ))
            ))
    getCond, setCond = mo.state(False)
    getBtnRow, setBtnRow = mo.state([])
    getChart, setChart = mo.state(None)
    getVariantConfig, setVariantConfig = mo.state(None)
    return (
        getBtnRow,
        getChart,
        getDf,
        getFrames,
        getPolling,
        getRowIndex,
        getVariantConfig,
        setBtnRow,
        setChart,
        setCond,
        setDf,
        setFrames,
        setPolling,
        setRowIndex,
        setVariantConfig,
    )


@app.cell
def _(MASS_COLUMNS, pl, pqpaths):
    def get_chunk():
        _df = pl.read_parquet(next(pqpaths))
        return _df.select(*list(MASS_COLUMNS.values()))

    df = get_chunk()
    return (df,)


@app.cell
def _(mo, setBtnRow, setPolling):
    start = mo.ui.run_button(label='Start', kind='success', on_change=lambda _: setPolling(True))
    stop = mo.ui.run_button(label='Stop', kind='danger', on_change=lambda _: setPolling(False))
    count = mo.ui.refresh(label="Fetching data...", default_interval=1.0, options=[0.11, 1.0, 5.0])

    btns = [start, stop]
    setBtnRow(btns)
    return btns, count, stop


@app.cell
def _(getPolling, setCond):
    if getPolling() == False:
        setCond(True)

    getPolling()
    return


@app.cell
def _(
    btns,
    count,
    df,
    getBtnRow,
    getFrames,
    getPolling,
    getRowIndex,
    mo,
    pl,
    setBtnRow,
    setDf,
    setFrames,
    setRowIndex,
    stop,
):
    if getPolling() == True:
        currentBtns = getBtnRow()
        if len(currentBtns) < 3:
            setBtnRow([*getBtnRow(), count])
        iRow = getRowIndex()
        print(f'Fetching networking data ;) which is for chunk row:\n{iRow}\n....')
        # await asyncio.sleep(5.0)
        currentFrames = getFrames()
        rowDf = df.slice(iRow, 1)
        currentFrames.append(rowDf)
        setFrames(currentFrames)
        setRowIndex(iRow + 1)
        # await asyncio.sleep(0.8)
        # setChart(generateChart(getDf()))
        setDf(pl.concat(getFrames()))

    if getPolling() == False:
        setBtnRow(btns)

    mo.stop(stop.value, 'Stopped!')
    return


@app.cell
def _(getBtnRow, mo):
    mo.hstack(getBtnRow(), justify="start")
    return


@app.cell
def _(getFrames, pl, plot_mass_fractions_from_worker_events):
    def generateChart(df):
        return plot_mass_fractions_from_worker_events(
            pl.concat([df, *getFrames()])
        )
    return (generateChart,)


@app.cell
def _(stop):
    if stop.value:
        print('stop')
    return


@app.cell
def _(generateChart, getDf, setChart):
    setChart(generateChart(getDf()))
    return


@app.cell
def _(getChart):
    currentChart = getChart()
    return


@app.cell
def _(getVariantConfig, mo, setVariantConfig):
    ncells_slider = mo.ui.slider(start=0, stop=10_000, step=1.0)
    dur_slider = mo.ui.slider(start=0.1, stop=10_000, step=0.1)

    if not getVariantConfig():
        setVariantConfig([])

    add_param_button = mo.ui.run_button(label='+', on_change=lambda _: setVariantConfig([*getVariantConfig(), {}]))
    variant_config = mo.ui.array(getVariantConfig())
    variant_stack = mo.hstack([variant_config, add_param_button], justify="start")
    return dur_slider, ncells_slider, variant_config, variant_stack


@app.cell
def _(dur_slider, mo, ncells_slider, variant_config, variant_stack):
    settings_tab = mo.vstack([
        mo.md(f'#### Number of Cells: {ncells_slider.value} | Duration: {dur_slider.value} | Variant Config: {variant_config.value}'),
        mo.accordion(items=dict(zip(
            ['Number of Cells', 'Duration', 'Variant Config'],
            [ncells_slider, dur_slider, variant_stack]
        )))
    ])
    return (settings_tab,)


@app.cell
def _(getBtnRow, getDf, mo, settings_tab, time):
    tabs = mo.ui.tabs({
        f'{mo.icon("bi:measuring-cup")}': mo.ui.data_explorer(getDf()),
        f'{mo.icon("bx:bar-chart-square")}': mo.lazy(getDf().plot.line(x='time')),
        f'{mo.icon("bi:sliders")}': settings_tab
    }, on_change=lambda _: time.sleep(0.22))

    btnStack = mo.hstack(getBtnRow(), justify="start")
    return (tabs,)


@app.cell
def _(tabs):
    tabs
    return


@app.cell
def _():
    return


@app.cell
def _():
    # eventsDf.plot.line(x='time')
    return


if __name__ == "__main__":
    app.run()
