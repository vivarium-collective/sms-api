import marimo

__generated_with = "0.18.1"
app = marimo.App(
    width="medium",
    app_title="Atlantis - Single Cell",
    layout_file="layouts/single_cell.grid.json",
)


@app.cell
def _():
    # /// script
    # [tool.marimo.display]
    # theme = "dark"
    # ///
    return


@app.cell
def _(mo):
    mo.md(r"""
    # EcoliSim: Interactive Simulation Interface
    Welcome to **EcoliSim**, a browser-based interface for running and analyzing whole-cell *E. coli* simulations.
    This notebook is powered by [Marimo](https://github.com/marimo-team/marimo) and provides lightweight access
    to *E. coli* models relevant to microbial dynamics, biomanufacturing, and antibiotic response.

    Use the controls in each section to simulate growth, visualize outcomes, and explore parameter spaces.
    """)
    return


@app.cell
def _():
    # create service with registerable callbacks
    # this service provides the data as needed specifically by the notebooks
    # have listeners for the registered callbacks

    import asyncio
    import json
    import time
    from collections.abc import Generator
    from contextlib import contextmanager
    from enum import Enum, StrEnum
    from pprint import pformat

    import altair as alt
    import marimo as mo
    import polars as pl
    from httpx import Client, HTTPStatusError, Timeout

    from sms_api.config import get_settings
    from sms_api.simulation.models import (
        BaseModel,
        EcoliExperiment,
        EcoliSimulationRequest,
        JobStatus,
        ParcaDataset,
        WorkerEvent,
    )
    # from app.api.simulations import EcoliSim
    # from app.api.client_wrapper import ClientWrapper

    # logger = logging.getLogger(__file__)

    def display_dto(dto: BaseModel | None = None) -> mo.Html | None:
        if not dto:
            return None
        return mo.md(f"```python\n{pformat(dto.dict())}\n```")

    return (
        Client,
        EcoliExperiment,
        EcoliSimulationRequest,
        Enum,
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
        get_settings,
        json,
        mo,
        pl,
        time,
    )


@app.cell
def _(Client, Generator, StrEnum, Timeout, contextmanager, get_settings):
    # -- api client and call setup -- #

    # SIMULATION_TEST_ID = 3

    def get_base_url() -> str:
        settings = get_settings()
        api_server_url = settings.marimo_api_server
        if not len(api_server_url):
            # api_server_url = "http://localhost:8000"
            api_server_url = "https://sms.cam.uchc.edu"
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
        with Client(base_url=base_url or get_base_url(), timeout=Timeout(timeout or 22.0)) as client:
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
                url = format_endpoint_url(ApiResource.SIMULATION, "parca", "versions")
                resp = client.get(url=url)
                resp.raise_for_status()
                return [ParcaDataset(**dataset) for dataset in resp.json()]
        except HTTPStatusError as e:
            raise HTTPStatusError(message=str(e))

    def on_run_simulation(request: EcoliSimulationRequest) -> EcoliExperiment:
        try:
            with api_client() as client:
                url = format_endpoint_url(ApiResource.SIMULATION, "run")
                request_payload = request.as_payload().dict()
                resp = client.post(url=url, json=request_payload)
                resp.raise_for_status()
                return EcoliExperiment(**resp.json())
        except HTTPStatusError as e:
            raise HTTPStatusError(message=str(e))

    def on_get_worker_events(simulation_id: int) -> list[WorkerEvent]:
        try:
            with api_client() as client:
                url = format_endpoint_url(ApiResource.SIMULATION, "run", "events")
                resp = client.get(url=url, params={"simulation_id": simulation_id})
                resp.raise_for_status()
                return [WorkerEvent(**event) for event in resp.json()]
        except HTTPStatusError as e:
            raise HTTPStatusError(message=str(e))

    def on_get_simulation_status(simulation_id: int) -> str:
        with api_client() as client:
            try:
                url = format_endpoint_url(ApiResource.SIMULATION, "run", "status")
                resp = client.get(url=url, params={"simulation_id": simulation_id})
                status = resp.json()["status"]
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
        variant_config: dict[str, dict[str, float]] | None = None,  # TODO: formalize this
    ) -> EcoliSimulationRequest:
        if not len(parca_datasets):
            raise ValueError("There are no datasets uploaded")
        active_parca_dataset: ParcaDataset = parca_datasets[-1]
        return EcoliSimulationRequest(
            parca_dataset_id=active_parca_dataset.database_id,
            simulator=active_parca_dataset.parca_dataset_request.simulator_version,
            variant_config=variant_config or {"named_parameters": {"param1": 0.5, "param2": 0.5}},
        )

    request: EcoliSimulationRequest = extract_simulation_request(parca_datasets)
    return (request,)


@app.cell
def _(alt, mo, pl):
    def default_chart():
        return mo.ui.altair_chart(
            alt.Chart(pl.DataFrame({"Time": 0.0, "Normalized Mass": 0.0}))
            .mark_line()
            .encode(x="Time", y="Normalized Mass")
        )

    return (default_chart,)


@app.cell
def _(JobStatus, default_chart, mo, pl):
    # set mutable state attributes (hooks, really)
    get_dataframes, set_dataframes = mo.state([])
    get_current_index, set_current_index = mo.state(0)
    get_is_polling, set_is_polling = mo.state(False)
    # get_chart, set_chart = mo.state(mo.ui.altair_chart(alt.Chart(pl.DataFrame({"time": 0.0})).mark_line().encode()))
    get_chart, set_chart = mo.state(default_chart())
    get_status, set_status = mo.state(JobStatus.WAITING)
    get_events, set_events = mo.state([])
    get_events_df, set_events_df = mo.state(pl.DataFrame())
    get_simulation_id, set_simulation_id = mo.state(None)
    get_stopped, set_stopped = mo.state(False)
    get_counter, set_counter = mo.state(0)
    get_paused, set_paused = mo.state(False)

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
        get_stopped,
        set_chart,
        set_counter,
        set_current_index,
        set_dataframes,
        set_events,
        set_events_df,
        set_is_polling,
        set_simulation_id,
        set_status,
        set_stopped,
        step_size,
    )


@app.cell
def _(mo, set_is_polling, set_stopped):
    def stop_simulation():
        set_is_polling(False)
        set_stopped(True)

    # set and display run/stop buttons
    run_simulation_button = mo.ui.run_button(
        label=f"{mo.icon('mdi:bacteria-outline')} Start", kind="success", tooltip="Run Simulation"
    )
    stop_simulation_button = mo.ui.run_button(
        label=f"{mo.icon('pajamas:stop')} Stop",
        kind="danger",
        tooltip="Stop Simulation",
        on_change=lambda _: stop_simulation(),
    )
    return run_simulation_button, stop_simulation_button


@app.cell
async def _(
    EcoliExperiment,
    asyncio,
    on_run_simulation,
    request,
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
    experiment,
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
    return (current_events,)


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
    set_counter,
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

    def on_poll(icounter: int | None = None):
        # if polling is turned on, get latest event data
        if get_is_polling():
            # small buffer -- let it breathe!
            time.sleep(1.1)
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

            if icounter:
                set_counter(icounter)
        else:
            print("Not polling")

    return (on_poll,)


@app.cell
def _(
    current_events,
    default_chart,
    get_chart,
    get_is_polling,
    get_stopped,
    mo,
    on_poll,
    run_simulation_button,
    set_chart,
    stop_simulation_button,
):
    # set latest render
    latest_chart = get_chart()
    set_chart(latest_chart)

    refresh = None
    if get_is_polling():
        refresh = mo.ui.refresh(
            label="Refreshing data...", options=[1.0, 5.0, 10.0], default_interval=5.0, on_change=lambda _: on_poll(_)
        )

    spinner = None
    if not get_stopped() and latest_chart is None:
        spinner = mo.status.spinner(title="Fetching data...")

    # ui stack with run button and latest render
    button_stack = [run_simulation_button, stop_simulation_button]
    stack_items = [
        mo.hstack(button_stack, justify="start"),
        # latest_chart
    ]

    # case: polling is started
    if refresh is not None:
        stack_items.append(refresh)

    # case: there are worker events: render chart!!
    if len(current_events):
        stack_items.append(latest_chart)

    # case: polling is started but chart is none
    if spinner is not None:
        stack_items.append(spinner)

    if get_stopped():
        refresh = None
        latest_chart = default_chart()
        set_chart(latest_chart)
        stack_items.append(mo.ui.text_area("Simulation Stopped.").callout(kind="danger"))
    return latest_chart, refresh, spinner, stack_items


@app.cell
def _(get_events_df, get_is_polling, mo, stack_items):
    data_explorer = mo.accordion({"Explore Data": mo.ui.data_explorer(get_events_df())})
    if get_is_polling():
        stack_items.append(data_explorer)
    return


@app.cell
def _(mo):
    # notebook (edit-mode) specific
    # sidenav = mo.sidebar([
    #     mo.md("# SMS API"),
    #     mo.nav_menu(
    #         {
    #             "https://sms-api.readthedocs.io/en/latest/": f"{mo.icon('pajamas:doc-text')} Documentation",
    #             "https://github.com/vivarium-collective/sms-api": f"{mo.icon('pajamas:github')} GitHub",
    #         },
    #         orientation="vertical",
    #     ),
    # ])

    # app menu content (upper-right-hand)
    menu_content = {
        "https://sms-api.readthedocs.io/en/latest/": f"{mo.icon('pajamas:doc-text')} SMS API Docs",
        "https://github.com/vivarium-collective/sms-api": f"{mo.icon('pajamas:github')} SMS API GitHub",
        "https://covertlab.github.io/vEcoli/": f"{mo.icon('cil:fingerprint')} vEcoli",
    }
    nav = mo.nav_menu(menu_content, orientation="horizontal")
    nav  # noqa: B018
    return nav


@app.cell
def _():
    # original working bundled ui stack
    # ui_stack = mo.vstack(stack_items)
    # ui_stack
    return


@app.cell
def _(get_events, get_events_df, latest_chart, mo):
    how_to = mo.md(f"""
            ### **How to use this tool**:
            - _Explore_: Explore the available simulation data in real-time and create customized analysis plots
            - _Visualize_: Visualize the simulation data in real time as a mass fraction plot.
            - _Configure_: Parameterize and configure the simulation. _(Coming Soon)_
            - _{mo.icon("pepicons-pop:refresh")}_: Click the dropdown menu to the left of the refresh button
                and select "off". The simulation will still run, but data retrieval will be paused.
        """).callout(kind="info")

    params = mo.md(f"""
        #### Duration
        {mo.ui.slider(start=1, stop=2800, show_value=True, value=2800)}
    """)

    tabs = mo.ui.tabs({
        f"{mo.icon('material-symbols:graph-3')} Explore": mo.ui.data_explorer(get_events_df()),
        f"{mo.icon('codicon:graph-line')} Visualize": latest_chart
        if len(get_events())
        else mo.md("Start the simulation. Results will display here.").callout("info"),
        f"{mo.icon('icon-park-twotone:experiment')} Configure": params,
        f"{mo.icon('material-symbols:help-outline-rounded')} Help": how_to,
    })

    how_to_display = mo.accordion({f"{mo.icon('material-symbols:help-outline-rounded')}": how_to})  # noqa: F841
    tabs  # noqa: B018
    return


@app.cell
def _(
    Enum,
    mo,
    refresh,
    run_simulation_button,
    spinner,
    stop_simulation_button,
):
    # -- buttons --

    btn_items = [run_simulation_button, stop_simulation_button]
    btn_stack = mo.hstack(btn_items, justify="start")

    class NotificationType(Enum):
        RUNNING: tuple[str, str] = ("processing simulation...", "success")
        PAUSED: tuple[str, str] = ("paused simulation...", "warn")
        STOPPED: tuple[str, str] = ("stopped simulation.", "danger")
        WAITING: tuple[str, str] = ("Press Start to run a simulation!", "info")

    def notification(_type: NotificationType) -> mo.md:
        msg, kind = _type.value
        v = f"...{msg}" if not kind == NotificationType.RUNNING else f"{msg}..."
        return mo.md(v).callout(kind=kind)

    row_items = [btn_stack]
    if refresh is not None:
        row_items.append(refresh)
        # if not get_counter() == refresh.value:
        #     set_counter(refresh.value)
        # else:
        #     set_paused(True)

    ui_items = []
    # if get_stopped():  # set ui notifications (really, button status)
    #     ui_items.append(notification(NotificationType.STOPPED))
    # if get_is_polling():
    #     ui_items.append(notification(NotificationType.RUNNING))
    if spinner is not None:
        ui_items.append(spinner)
    ui_items.insert(0, mo.hstack(row_items, justify="start"))

    # if get_paused():
    #     ui_items.append(notification(NotificationType.PAUSED))
    return NotificationType, notification, ui_items


@app.cell
def _(mo, ui_items):
    row_stack = mo.vstack(ui_items)
    row_stack
    return


@app.cell
def _(NotificationType, get_is_polling, get_stopped, notification):
    notification_type = notification(NotificationType.WAITING)
    if get_stopped():  # set ui notifications (really, button status)
        notification_type = notification(NotificationType.STOPPED)
    if get_is_polling():
        notification_type = notification(NotificationType.RUNNING)

    notification_type
    return


@app.cell
def _(mo):
    get_now, set_now = mo.state(None)
    get_wall, set_wall = mo.state(0.0)
    return get_now, get_wall, set_now, set_wall


@app.cell
def _(
    get_now,
    run_simulation_button,
    set_now,
    set_wall,
    stop_simulation_button,
    time,
):
    if run_simulation_button.value:
        set_now(time.time())

    if stop_simulation_button.value:
        dur = time.time() - get_now()
        set_wall(dur)
    return


@app.cell
def _(get_wall):
    get_wall()
    return


@app.cell
def _(spinner):
    spinner
    return


@app.cell
def _():
    import requests

    from sms_api.simulation.models import SimulationConfig

    def post_wcm_config(config: dict, config_id: str = "test", url_base: str = "http://localhost:8888"):
        """
        Posts a WCM experiment configuration to the server.

        Args:
            config: Dictionary containing the JSON configuration.
            config_id: Identifier for the config (used in URL query param).
            url_base: Base URL of the WCM server.

        Returns:
            Response object from requests.
        """
        url = f"{url_base}/wcm/experiment/config?config_id={config_id}"

        headers = {"accept": "application/json", "Content-Type": "application/json"}

        response = requests.post(url, headers=headers, json=config)

        # Raise exception if request failed
        response.raise_for_status()

        # Return JSON content
        return response.json()

    return SimulationConfig, post_wcm_config, requests


@app.cell
def _(requests):
    def post_wcm_experiment(config_id: str, overrides=None, metadata=None, url_base: str = "http://localhost:8888"):
        """
        Post to the /wcm/experiment endpoint to start an experiment run.

        Args:
            config_id: The config_id to use in the URL query parameter.
            overrides: Dict of overrides or None.
            metadata: Dict of metadata or None.
            url_base: Base URL of the WCM server.

        Returns:
            Parsed JSON response.
        """
        url = f"{url_base}/wcm/experiment?config_id={config_id}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {"overrides": overrides, "metadata": metadata if metadata is not None else {}}

        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    return (post_wcm_experiment,)


@app.cell
def _(mo):
    mo.md(r"""
    ### Customize and Upload Config
    """)
    return


@app.cell
def _(SimulationConfig):
    config = SimulationConfig.from_base()
    config
    return (config,)


@app.cell
def _(config, mo):
    dropdown = mo.ui.dropdown(options=config.model_dump())
    return


@app.cell
def _(config, json, mo):
    d = {}
    for k, v in config.model_dump().items():
        if isinstance(v, dict):
            d[k] = mo.ui.dictionary({kv: mo.ui.text(value=json.dumps(vv)) for kv, vv in v.items()})
        elif isinstance(v, list):
            d[k] = mo.ui.array([mo.ui.text(json.dumps(val)) for val in v])
        else:
            d[k] = mo.ui.text(json.dumps(v))
    config_ui = mo.ui.dictionary({**d})
    return (config_ui,)


@app.cell
def _(config_ui):
    config_ui
    return


@app.cell
def _(mo):
    get_config_ui, set_config_ui = mo.state([])
    get_config, set_config = mo.state(None)
    return get_config, get_config_ui, set_config, set_config_ui


@app.cell
def _(config, mo, set_config_ui):
    multiselect = mo.ui.multiselect(options=config.model_dump(), on_change=lambda selected: set_config_ui(selected))
    return (multiselect,)


@app.cell
def _(multiselect):
    multiselect
    return


@app.cell
def _(config, get_config_ui, json, mo):
    arr = {}
    for param in get_config_ui():
        i = list(config.model_dump().values()).index(param)
        arr[list(config.model_dump().keys())[i]] = mo.ui.text(json.dumps(list(config.model_dump().values())[i]))
    ui = mo.ui.dictionary(arr, label="Simulation Configuration")
    return (ui,)


@app.cell
def _(SimulationConfig, json, set_config, ui):
    set_config(SimulationConfig(experiment_id="single_cell_test", **{k: json.loads(v) for k, v in ui.value.items()}))
    return


@app.cell
def _(get_config):
    simconfig = get_config()
    return (simconfig,)


@app.cell
def _(simconfig):
    simconfig.experiment_id = "ui_test"
    return


@app.cell
def _(post_wcm_config, simconfig):
    config_id = post_wcm_config(config_id="test", config=simconfig.model_dump()).get("config_id")
    return (config_id,)


@app.cell
def _(config_id):
    config_id
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Use that config to run an experiment workflow
    """)
    return


@app.cell
def _(config_id, post_wcm_experiment):
    ecoli_experiment = post_wcm_experiment(config_id=config_id, overrides=None, metadata={})
    return (ecoli_experiment,)


@app.cell
def _(ecoli_experiment):
    ecoli_experiment
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
