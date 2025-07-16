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
    import os
    import json
    from pprint import pp
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
        ParcaDataset
    )
    from sms_api.config import get_settings
    from app.api.simulations import EcoliSim
    from app.api.client_wrapper import ClientWrapper
    return (
        Client,
        EcoliExperiment,
        EcoliSimulationRequest,
        Generator,
        HTTPStatusError,
        ParcaDataset,
        StrEnum,
        Timeout,
        WorkerEvent,
        alt,
        contextmanager,
        get_settings,
        mo,
        pl,
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
    def api_client(base_url: str | None = None) -> Generator[Client, None, None]:
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
            timeout=Timeout(11.11)
        ) as client:
            yield client


    class ApiResource(StrEnum):
        SIMULATOR = "simulator"
        SIMULATION = "simulation"


    def format_endpoint_url(resource: ApiResource, *subpaths):
        base_url = get_base_url()
        return f"{base_url}/{resource}/{'/'.join(list(subpaths))}"

    # client = ClientWrapper(base_url=base_url)
    return ApiResource, SIMULATION_TEST_ID, api_client, format_endpoint_url


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
        dataframes = []
        if events:
            for event in events:
                event_data = event.model_dump()
                selected_keys = select_keys(event_data["mass"], list(MAPPING.values()))
                # selected_keys['time'] = event.time
                df_event = pl.DataFrame({key: event.mass[key] for key in selected_keys})
                df_event = df_event.with_columns(pl.lit(event.time).alias("time"))
                dataframes.append(df_event)
        return pl.concat(dataframes, how="vertical_relaxed").sort("time")

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

    try:
        parca_datasets = on_get_parcas()
    except ValueError as e:
        print(e)
        parca_datasets = None
    return on_get_worker_events, parca_datasets


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
    return


@app.cell
def _(EcoliExperiment):
    # run the simulation
    experiment: EcoliExperiment | None = None  # on_run_simulation()
    return (experiment,)


@app.cell
def _(
    EcoliExperiment,
    SIMULATION_TEST_ID,
    experiment: "EcoliExperiment | None",
):
    # -- data prep helpers -- #

    # TODO: simulation id comes from simulation run DTO (EcoliExperiment)
    # placeholder: simulation_id = experiment.database_id
    def get_simulation_id(experiment: EcoliExperiment | None = None) -> int:
        return experiment.simulation.database_id if experiment else SIMULATION_TEST_ID

    simulation_id = get_simulation_id(experiment)
    return (simulation_id,)


@app.cell
def _(get_events_dataframe, on_get_worker_events, simulation_id):
    worker_events = on_get_worker_events(simulation_id)
    simulation_events_df = get_events_dataframe(worker_events)
    return (simulation_events_df,)


@app.cell
def _(mo):
    if not hasattr(mo.state, "dataframes"):
        mo.state.dataframes = []
    if not hasattr(mo.state, "current_index"):
        mo.state.current_index = 0

    step_size = 10  # number of rows to append per button press
    plt_button = mo.ui.run_button(label="Plot Mass Fractions")
    return plt_button, step_size


@app.cell
def _(
    mo,
    pl,
    plot_mass_fractions_from_worker_events,
    plt_button,
    simulation_events_df,
    step_size,
):
    if plt_button.value:
        next_index = mo.state.current_index
        end_index = min(next_index + step_size, simulation_events_df.height)
        if next_index < simulation_events_df.height:
            mo.state.dataframes.append(simulation_events_df.slice(next_index, end_index - next_index))
            mo.state.current_index = end_index

    # Display chart
    def display_chart():
        if mo.state.dataframes:
            combined_df = pl.concat(mo.state.dataframes)
            chart = plot_mass_fractions_from_worker_events(combined_df)
            return mo.vstack([plt_button, chart])
        else:
            return mo.vstack([plt_button, mo.md("Press the button to start streaming.")])

    display_chart()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
