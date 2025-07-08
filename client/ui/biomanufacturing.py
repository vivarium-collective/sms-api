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

    from client.api.antibiotic import EcoliSim

    return EcoliSim, mo, np


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Biomanufacturing

    This section focuses on simulations of **engineered E. coli strains** designed for chemical or protein production.

    Use this to:

    - Model biomass vs. product tradeoffs
    - Evaluate production stability over time
    - Compare strain variants under different feeding strategies
    """
    )
    return


if __name__ == "__main__":
    app.run()
