# Minimal working functions for Antibiotics-API notebook prototype
# These are dummy implementations returning synthetic data for prototyping

import dataclasses as dc

import numpy as np
from data_model.base import BaseClass
from matplotlib import pyplot as plt


@dc.dataclass
class AntibioticParams(BaseClass):
    # TODO: add more here
    dose: float = 1.0
    sensitivity: float = 1.0
    mic: float = 3.0
    rate: float = 0.3


@dc.dataclass
class AntibioticConfig(BaseClass):
    name: str
    params: AntibioticParams


@dc.dataclass
class AntibioticResponse(BaseClass):
    """Antibiotic Response Simulation Output structure"""

    antibiotic_name: str
    time: list
    pbp2_binding: list
    wall_integrity: list
    lysis_prob: list


@dc.dataclass
class CellTrajectory(BaseClass):
    time: list
    lysis_prob: list


@dc.dataclass
class Curve(BaseClass):
    dose: list
    survival: list


@dc.dataclass
class MIC(Curve):
    """Minimum Inhibitory Concentration"""

    pass


@dc.dataclass
class PAP(Curve):
    """Population Analysis Profile"""

    pass


# 1. Simulate mecillinam response
def simulate_antibiotic(name: str, params: AntibioticParams) -> AntibioticResponse:
    time = np.linspace(0, 10, 100)
    pbp2_binding = 1 - np.exp(-params.dose * time / 10)
    wall_integrity = np.exp(-pbp2_binding * time / 5)
    lysis_prob = 1 - wall_integrity

    return AntibioticResponse(**{
        "antibiotic_name": name,
        "time": time.tolist(),
        "pbp2_binding": pbp2_binding.tolist(),
        "wall_integrity": wall_integrity.tolist(),
        "lysis_prob": lysis_prob.tolist(),
    })


# 2. MIC curve simulation
def get_MIC_curve(params: AntibioticParams) -> MIC:
    doses = np.logspace(-2, 1, 20)
    survival = np.exp(-doses / params.sensitivity)
    return MIC(**{"dose": doses.tolist(), "survival": survival.tolist()})


# 3. PAP curve simulation
def get_PAP_curve(params: AntibioticParams) -> PAP:
    doses = np.linspace(0, 10, 20)
    survival = 1 / (1 + np.exp(doses - params.mic))
    return PAP(**{"dose": doses.tolist(), "survival": survival.tolist()})


# 4. Single-cell trajectories simulation
def get_single_cell_trajectories(n_cells: int, params: AntibioticParams) -> list[CellTrajectory]:
    time = np.linspace(0, 10, 100)
    cells = []
    for _ in range(n_cells):
        rate = np.random.normal(loc=params.rate, scale=0.05)
        trajectory = 1 - np.exp(-rate * time)
        cells.append(CellTrajectory(**{"time": time.tolist(), "lysis_prob": trajectory.tolist()}))
    return cells


# 5. List of parameters
def list_available_parameters():
    return {"dose": [0.01, 10], "sensitivity": [0.1, 10], "mic": [0.5, 10], "rate": [0.1, 1.0]}


# 6. Parameter scan
def run_parameter_scan(param_name, values, fixed_params):
    results = []
    for v in values:
        p = fixed_params.copy()
        p[param_name] = v
        mic_curve = get_MIC_curve(p)
        results.append(mic_curve["survival"])
    return {"param": param_name, "values": values, "survival_curves": results}


# -- plots -- #


def plot_mic_curve(mic_curve, title="MIC Curve: Survival vs. Antibiotic Dose"):
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


def plot_pap_curve(pap_curve, title="PAP Curve: Population Survival vs. Dose"):
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


def plot_antibiotic_response(response, title="Simulated Antibiotic Response Over Time"):
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


def plot_single_cell_trajectories(trajectories, title="Single-Cell Lysis Trajectories"):
    plt.figure(figsize=(8, 5))
    for i, cell in enumerate(trajectories):
        plt.plot(cell["time"], cell["lysis_prob"], label=f"Cell {i + 1}", alpha=0.7)

    plt.title(title, fontsize=14)
    plt.xlabel("Time (hr)", fontsize=12)
    plt.ylabel("Lysis Probability", fontsize=12)
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.show()


def plot_parameter_scan(scan_results, title="Parameter Scan: Survival Curves"):
    param_name = scan_results["param"]
    values = scan_results["values"]
    survival_curves = scan_results["survival_curves"]

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
