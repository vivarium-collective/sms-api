from typing import cast

import altair as alt
import numpy as np
import polars as pl
from matplotlib import pyplot as plt

COLORS = [
    "#1f77b4",  # blue
    "#ff7f0e",  # orange
    "#2ca02c",  # green
    "#d62728",  # red
    "#9467bd",  # purple
    "#8c564b",  # brown
    "#e377c2",  # pink
]


def plot_from_dfs(
    dataframes: list[pl.DataFrame],
    *,
    labels: list[str] | None = None,
) -> alt.Chart:
    """Plot mass fraction summary from a list of Polars DataFrames (historical simulations).

    Args:
        dataframes (list[pl.DataFrame]): List of DataFrames with time and mass columns.
        labels (list[str] | None): Optional labels for each dataframe/simulation.
    """

    mass_columns = {
        "Protein": "listeners__mass__protein_mass",
        "tRNA": "listeners__mass__tRna_mass",
        "rRNA": "listeners__mass__rRna_mass",
        "mRNA": "listeners__mass__mRna_mass",
        "DNA": "listeners__mass__dna_mass",
        "Small Mol.s": "listeners__mass__smallMolecule_mass",
        "Dry": "listeners__mass__dry_mass",
    }

    all_melted: list[pl.DataFrame] = []
    labels = labels or [f"sim_{i}" for i in range(len(dataframes))]

    for label, df in zip(labels, dataframes):
        # Compute average mass fractions
        fractions = {k: (df[v] / df["listeners__mass__dry_mass"]).mean() for k, v in mass_columns.items()}

        # Prepare normalized time and mass columns
        # new_columns = {
        #     "Time (min)": (df["time"] - df["time"].min()) / 60,
        #     **{f"{k} ({fractions[k]:.3f})": df[v] / df[v][0] for k, v in mass_columns.items()},
        # }

        new_columns = {
            "Time (min)": (df["time"] - df["time"].min()) / 60,
            **{
                f"{k} ({fractions[k]:.3f})": df[v_str] / df[v_str][0]
                for k, v in mass_columns.items()
                if (v_str := v.decode() if isinstance(v, bytes) else v)
            },
        }

        mass_fold_change_df = pl.DataFrame(new_columns)

        melted = mass_fold_change_df.melt(
            id_vars="Time (min)",
            variable_name="Submass",
            value_name="Mass (normalized by t = 0 min)",
        ).with_columns(pl.lit(label).alias("Simulation"))

        all_melted.append(melted)

    final_df = pl.concat(all_melted, how="vertical")

    chart = (
        alt.Chart(final_df)
        .mark_line()
        .encode(
            x=alt.X("Time (min):Q", title="Time (min)"),
            y=alt.Y("Mass (normalized by t = 0 min):Q"),
            color=alt.Color("Submass:N", scale=alt.Scale(range=COLORS)),
            strokeDash=alt.StrokeDash("Simulation:N"),
        )
        .properties(title="Mass components across simulations (fractions in legend)")
    )

    return chart


def plot_mic_curve(mic_curve: dict[str, list[float]], title: str = "MIC Curve: Survival vs. Antibiotic Dose") -> None:
    """
    Plot a MIC (Minimum Inhibitory Concentration) survival curve.

    Parameters:
    - mic_curve (dict): Output from get_MIC_curve with 'dose' and 'survival' arrays
    - title (str): Title of the plot
    """
    doses = mic_curve["dose"]
    survival = mic_curve["survival"]

    plt.figure(figsize=(8, 5))
    plt.semilogx(doses, survival, marker="o", linestyle="-", color="teal", linewidth=2)

    plt.title(title, fontsize=14)
    plt.xlabel("Mecillinam Dose (µg/mL)", fontsize=12)
    plt.ylabel("Survival Fraction", fontsize=12)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.ylim(0, 1.05)
    plt.tight_layout()
    plt.show()


def plot_pap_curve(pap_curve: dict[str, list[float]], title: str = "PAP Curve: Population Survival vs. Dose") -> None:
    doses = pap_curve["dose"]
    survival = pap_curve["survival"]

    plt.figure(figsize=(8, 5))
    plt.plot(doses, survival, marker="o", linestyle="-", color="darkorange", linewidth=2)
    plt.title(title, fontsize=14)
    plt.xlabel("Mecillinam Dose (µg/mL)", fontsize=12)
    plt.ylabel("Survival Fraction", fontsize=12)
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.ylim(0, 1.05)
    plt.tight_layout()
    plt.show()


def plot_antibiotic_response(
    response: dict[str, list[float]], title: str = "Simulated Antibiotic Response Over Time"
) -> None:
    time = response["time"]

    plt.figure(figsize=(10, 6))
    plt.plot(time, response["pbp2_binding"], label="PBP2 Binding", linewidth=2)
    plt.plot(time, response["wall_integrity"], label="Wall Integrity", linewidth=2)
    plt.plot(time, response["lysis_prob"], label="Lysis Probability", linewidth=2)

    plt.title(title, fontsize=14)
    plt.xlabel("Time (hr)", fontsize=12)
    plt.ylabel("Value", fontsize=12)
    plt.legend()
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


def plot_single_cell_trajectories(
    trajectories: list[dict[str, list[float]]], title: str = "Single-Cell Lysis Trajectories"
) -> None:
    plt.figure(figsize=(8, 5))
    for i, cell in enumerate(trajectories):
        plt.plot(cell["time"], cell["lysis_prob"], label=f"Cell {i + 1}", alpha=0.7)

    plt.title(title, fontsize=14)
    plt.xlabel("Time (hr)", fontsize=12)
    plt.ylabel("Lysis Probability", fontsize=12)
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


def plot_parameter_scan(
    scan_results: dict[str, str | list[list[float]]], title: str = "Parameter Scan: Survival Curves"
) -> None:
    param_name = cast(str, scan_results["param"])
    values = cast(list[list[float]], scan_results["values"])
    survival_curves = cast(list[list[float]], scan_results["survival_curves"])

    doses = np.logspace(-2, 1, len(survival_curves[0]))  # Assumes same x-axis

    plt.figure(figsize=(10, 6))
    for value, survival in zip(values, survival_curves):
        label = f"{param_name} = {value:.2f}"
        plt.semilogx(doses, survival, label=label, linewidth=2)

    plt.title(title, fontsize=14)
    plt.xlabel("Mecillinam Dose (µg/mL)", fontsize=12)
    plt.ylabel("Survival Fraction", fontsize=12)
    plt.ylim(0, 1.05)
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.legend(title=param_name)
    plt.tight_layout()
    plt.show()
