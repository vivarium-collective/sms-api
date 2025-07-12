from typing import cast

import numpy as np
from matplotlib import pyplot as plt


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
