import concurrent.futures
import time

import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm


class EcoliSim:
    def __init__(self, endpoint_url="http://localhost:8000/simulate", seed=None):
        self.endpoint_url = endpoint_url
        self.simulated_time = 40  # minutes
        self.dt = 0.2  # minutes
        self.time_points = np.arange(0, self.simulated_time + self.dt, self.dt)
        self.components = ["Protein", "rRNA", "tRNA", "mRNA", "DNA", "Small Mol."]
        self.rng = np.random.default_rng(seed)

    ######################
    # 1. SINGLE CELL SIM #
    ######################

    def simulate_single_cell(self):
        self.mass_fractions = {}
        base = np.exp(self.time_points / self.simulated_time)

        for comp in self.components:
            noise = self.rng.normal(0, 0.02, len(self.time_points))
            self.mass_fractions[comp] = (base / base[0]) * (0.9 + 0.2 * self.rng.random()) + noise

        print("[EcoliSim] Single cell simulation complete.")

    def display_single_cell_mass_fractions(self):
        fig, ax = plt.subplots(figsize=(8, 6))
        for comp, values in self.mass_fractions.items():
            ax.plot(self.time_points, values, label=comp)
        ax.axhline(2, linestyle="--", color="gray")
        ax.set_xlabel("Time (min)")
        ax.set_ylabel("Normalized mass")
        ax.set_title("E. coli Single-Cell Mass Fractions")
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.4)
        plt.tight_layout()
        return fig

    ######################
    # 2. MULTI-CELL SIM  #
    ######################

    def simulate_multiple_cells(self, n_cells=10):
        self.multi_cell_total_mass = []

        for _ in range(n_cells):
            growth = np.exp(self.time_points / self.simulated_time)
            variation = self.rng.normal(0, 0.05, len(self.time_points))
            mass = growth + variation
            self.multi_cell_total_mass.append(mass)

        print(f"[EcoliSim] Simulated {n_cells} cells for total mass trajectories.")

    def display_multi_cell_total_masses(self):
        fig, ax = plt.subplots(figsize=(8, 5))
        for i, mass in enumerate(self.multi_cell_total_mass):
            ax.plot(self.time_points, mass, alpha=0.6, label=f"Cell {i + 1}")
        ax.set_xlabel("Time (min)")
        ax.set_ylabel("Total mass (a.u.)")
        ax.set_title("E. coli Total Mass for Multiple Cells")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend()
        plt.tight_layout()
        return fig

    ######################
    # 3. MIC CURVE SIM   #
    ######################

    def simulate_cell_survival(self, dose):
        time.sleep(self.rng.uniform(0.01, 0.03))  # simulate delay
        survival_chance = np.exp(-0.3 * dose)
        return self.rng.random() < survival_chance

    def simulate_batch_survival(self, dose, n_cells):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(
                tqdm(
                    executor.map(self.simulate_cell_survival, [dose] * n_cells),
                    total=n_cells,
                    desc=f"Dose {dose:.2f}",
                    leave=False,
                    ncols=70,
                )
            )
        return sum(results) / n_cells

    def measure_mic_curve(self, doses, n_cells=100):
        self.mic_results = {}
        print("[EcoliSim] Starting MIC curve simulation...")
        for dose in doses:
            self.mic_results[dose] = self.simulate_batch_survival(dose, n_cells)
        print("[EcoliSim] MIC curve simulation complete.")

    def display_mic_curve(self):
        doses = sorted(self.mic_results.keys())
        survivals = [self.mic_results[d] for d in doses]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(doses, survivals, marker="o", linestyle="-", color="darkgreen")
        ax.set_xlabel("Antibiotic Dose (µg/mL)")
        ax.set_ylabel("Survival Fraction")
        ax.set_title("E. coli MIC Curve")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.axhline(0.1, color="red", linestyle="--", label="10% survival threshold")
        ax.legend()
        plt.tight_layout()
        return fig
