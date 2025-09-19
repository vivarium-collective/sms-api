import marimo

__generated_with = "0.14.17"
app = marimo.App(
    width="medium",
    app_title="Atlantis - Single Cell",
    layout_file="layouts/experiment.grid.json",
)


@app.cell
def _(mo):
    mo.md(
        r"""
    # SMS Interactive Simulation Interface
    Welcome to **SMS**, a browser-based interface for running and analyzing whole-cell *E. coli* simulations. This notebook is powered by [Marimo](https://github.com/marimo-team/marimo) and provides lightweight access to *E. coli* models relevant to microbial dynamics, biomanufacturing, and antibiotic response.

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
    from enum import StrEnum, Enum
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
        JobStatus,
    )
    from sms_api.config import get_settings
    from app.api.simulations import EcoliSim
    from app.api.client_wrapper import ClientWrapper

    logger = logging.getLogger(__file__)

    class ApiResource(StrEnum):
        SIMULATOR = "simulator"
        SIMULATION = "simulation"

    class Colors(StrEnum):
        BLUE = ("#1f77b4",)
        ORANGE = ("#ff7f0e",)
        GREEN = ("#2ca02c",)
        RED = ("#d62728",)
        PURPLE = ("#9467bd",)
        BROWN = ("#8c564b",)
        PINK = ("#e377c2",)

    def display_dto(dto: BaseModel | None = None) -> mo.Html | None:
        from pprint import pformat

        if not dto:
            return None
        return mo.md(f"```python\n{pformat(dto.dict())}\n```")

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
        with Client(base_url=base_url or get_base_url(), timeout=Timeout(timeout or 22.0)) as client:
            yield client

    def format_endpoint_url(resource: ApiResource, *subpaths):
        base_url = get_base_url()
        return f"{base_url}/{resource}/{'/'.join(list(subpaths))}"

    return Path, json, mo, pl


@app.cell
def _(mo):
    # notebook (edit-mode) specific
    sidenav = mo.sidebar([
        mo.md("# SMS API"),
        mo.nav_menu(
            {
                "https://sms-api.readthedocs.io/en/latest/": f"{mo.icon('pajamas:doc-text')} Documentation",
                "https://github.com/vivarium-collective/sms-api": f"{mo.icon('pajamas:github')} GitHub",
            },
            orientation="vertical",
        ),
    ])

    # app menu content (upper-right-hand)
    menu_content = {
        "https://sms-api.readthedocs.io/en/latest/": f"{mo.icon('pajamas:doc-text')} SMS API Docs",
        "https://github.com/vivarium-collective/sms-api": f"{mo.icon('pajamas:github')} SMS API GitHub",
        "https://covertlab.github.io/vEcoli/": f"{mo.icon('cil:fingerprint')} vEcoli",
    }
    nav = mo.nav_menu(menu_content, orientation="horizontal")
    nav
    return


@app.cell
def _():
    import requests
    from sms_api.simulation.models import SimulationConfig

    def wcm_config(config: dict, config_id: str = "test", url_base: str = "http://localhost:8888"):
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

    def wcm_experiment(config_id: str, overrides=None, metadata=None, url_base: str = "http://localhost:8888"):
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
        metadataa = {
            "additionalProp1": "string",
            "additionalProp2": "string",
            "additionalProp3": "string"
        }
        payload = {"overrides": {}, "metadata": metadataa}

        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()

    def wcm_status(experiment_tag: str, url_base: str = "http://localhost:8888"):
        url = f'http://localhost:8888/experiments/status?experiment_tag={experiment_tag}'
        # url = f"{url_base}/wcm/experiment?config_id={config_id}"
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }

        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    return SimulationConfig, wcm_experiment, wcm_status


@app.cell
def _(mo):
    mo.md(r"""### Customize and Upload Config""")
    return


@app.cell
def _(Path, SimulationConfig):
    config = SimulationConfig.from_file(Path("assets/sms_single_cell.json"))
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
    config_ui = mo.ui.dictionary({**d}, label="Simulation Configuration")
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
    multiselect = mo.ui.multiselect(
        options=config.model_dump(),
        on_change=lambda selected: set_config_ui(selected),
        label="Select Configuration Options",
    )
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
    set_config(SimulationConfig(**{k: json.loads(v) for k, v in ui.value.items()}))
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
def _(mo):
    mo.md(r"""### Use that config to run an experiment workflow""")
    return


@app.cell
def _(mo):
    get_config_id, set_config_id = mo.state(None)
    get_events, set_events = mo.state([])
    return get_config_id, get_events, set_config_id


@app.cell
def _(mo, set_config_id):

    drop = mo.ui.dropdown(["multigeneration", "single"], value="single", on_change=lambda _: set_config_id(f"sms_{_}"), label="Experiment Type: ")
    # ecoli_experiment = wcm_experiment(config_id=config_id, overrides=None, metadata={})
    drop

    return (drop,)


@app.cell
def _(drop):
    confid = drop.value
    confid
    return


@app.cell
def _(mo):
    run_button = mo.ui.run_button(label="Launch Simulation")
    return


@app.cell
def _(get_events, latest_chart, mo, pl):
    how_to = mo.md(f"""
                ### **How to use this tool**:
                - _Explore_: Explore the available simulation data in real-time and create customized analysis plots
                - _Visualize_: Visualize the simulation data in real time as a mass fraction plot.
                - _Configure_: Parameterize and configure the simulation. _(Coming Soon)_
                - _{mo.icon("pepicons-pop:refresh")}_: Click the dropdown menu to the left of the refresh button and select "off". The simulation will still run, but data retrieval will be paused.
            """).callout(kind="info")

    params = mo.md(f"""
        #### Duration
        {mo.ui.slider(start=1, stop=2800, show_value=True, value=2800)}
    """)



    tabs = mo.ui.tabs({
        f"{mo.icon('material-symbols:graph-3')} Explore": mo.ui.data_explorer(pl.DataFrame()),
        f"{mo.icon('codicon:graph-line')} Visualize": latest_chart
        if len(get_events())
        else mo.md("Start the simulation. Results will display here.").callout("info"),
        f"{mo.icon('icon-park-twotone:experiment')} Configure": params,
        f"{mo.icon('material-symbols:help-outline-rounded')} Help": how_to,
    })

    how_to_display = mo.accordion({f"{mo.icon('material-symbols:help-outline-rounded')}": how_to})
    return (tabs,)


@app.cell
def _(tabs):
    tabs
    return


@app.cell
def _(mo):
    mo.md(
        r"""
    # SMS: Interactive Simulation Interface
    Welcome to **SMS Smartbooks**, a browser-based interface for running and analyzing whole-cell *E. coli* simulations. This notebook is powered by [Marimo](https://github.com/marimo-team/marimo) and provides lightweight access to *E. coli* models relevant to microbial dynamics, biomanufacturing, and antibiotic response.

    Use the controls in each section to simulate growth, visualize outcomes, and explore parameter spaces.
    """
    )
    return


@app.cell
def _(mo):
    run_simulation_button = mo.ui.run_button(
            label=f"{mo.icon('mdi:bacteria-outline')} Start", kind="success", tooltip="Launch Experiment"
        )
    stop_simulation_button = mo.ui.run_button(
        label=f"{mo.icon('pajamas:stop')} Stop",
        kind="danger",
        tooltip="Stop Experiment"
    )
    return run_simulation_button, stop_simulation_button


@app.cell
def _(run_simulation_button):
    run_simulation_button
    return


@app.cell
def _(mo):
    get_exp, set_exp = mo.state(None)
    return get_exp, set_exp


@app.cell
def _(stop_simulation_button):
    stop_simulation_button
    return


@app.cell
def _(drop, get_config_id, run_simulation_button, set_exp, wcm_experiment):
    if run_simulation_button.value:
        if get_config_id() is not None:
            experiment = wcm_experiment(config_id=f'sms_{drop.value}')
            set_exp(experiment)
            print(experiment)
    return


@app.cell
def _(get_exp, wcm_status):
    status = None 

    if get_exp() is not None:
        statusdata = wcm_status(get_exp())
        msg = f"""\
        ### Experiment {statusdata['id']}: {statusdata['status']}
        """
    return


@app.cell
def _(get_exp):
    get_exp()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
