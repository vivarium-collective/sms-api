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

    import marimo as mo
    import polars as pl
    import altair as alt
    from altair import Chart
    from fastapi import HTTPException
    from httpx import AsyncClient, QueryParams, Client

    from sms_api.simulation.models import (
        SimulatorVersion,
        EcoliSimulationRequest,
        EcoliExperiment,
        WorkerEvent,
        ParcaDataset
    )
    from app.api.simulations import EcoliSim
    from app.api.client_wrapper import ClientWrapper


    base_url = "http://localhost:8888/core"
    client = ClientWrapper(base_url=base_url)
    return Client, WorkerEvent, alt, mo, pl


@app.cell
def _(WorkerEvent, alt, mo, pl):
    # 1. upload simulator
    # 2. upload parca
    # 3. pin {simulator_id: ..., parca_id: ...}
    # 4. run simulation using #3
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
def _():
    # chunks_dir = Path("assets/tests/test_history")
    # mass_data = get_parquet_mass_data(chunks_dir, MASS_COLUMNS)
    # simulation_df = get_masses_dataframe(mass_data)
    return


@app.cell
def _(Client):
    def get_worker_events(simulation_id: int):
        with Client() as _client:
            resp = _client.get(url="http://localhost:8888/core/simulation/run/events", params={"simulation_id": 3})
            resp.raise_for_status()
            return resp.json()

    # placeholder: simulation_id = experiment.database_id
    simulation_id = 3
    worker_event_data = get_worker_events(simulation_id)
    return (worker_event_data,)


@app.cell
def _(WorkerEvent, get_events_dataframe, worker_event_data):
    worker_events = [WorkerEvent(**event) for event in worker_event_data]
    simulation_df = get_events_dataframe(worker_events)
    return (simulation_df,)


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
    simulation_df,
    step_size,
):
    if plt_button.value:
        next_index = mo.state.current_index
        end_index = min(next_index + step_size, simulation_df.height)
        if next_index < simulation_df.height:
            mo.state.dataframes.append(simulation_df.slice(next_index, end_index - next_index))
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
