import marimo

__generated_with = "0.13.15"
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
    import marimo as mo
    import numpy as np

    from app.api.simulations import EcoliSim

    return EcoliSim, mo, np


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Antibiotics

    Simulate the effects of the antibiotic mecillinam on *E. coli* populations.
    """
    )
    return


@app.cell
def _(mo):
    sim3_n_cells = mo.ui.slider(1, 50, value=10, label="Number of Cells")
    sim3_doses = mo.ui.slider(2, 20, value=10, label="Number of Dose Levels")
    sim3_run_button = mo.ui.run_button(label="Run Simulation")

    mo.vstack([sim3_n_cells, sim3_doses, sim3_run_button])
    return sim3_doses, sim3_n_cells, sim3_run_button


@app.cell
def _(EcoliSim, np, sim3_doses, sim3_n_cells, sim3_run_button):
    fig3 = None
    if sim3_run_button.value:
        dose_range = np.linspace(0, 10, sim3_doses.value)
        sim3 = EcoliSim()
        sim3.measure_mic_curve(dose_range, n_cells=sim3_n_cells.value)
        fig3 = sim3.display_mic_curve()
    fig3
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
