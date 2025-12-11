import marimo

__generated_with = "0.13.15"
app = marimo.App(width="medium")


@app.cell
def _():
    # /// script
    # [tool.marimo.display]
    # theme = "dark"
    # ///
    return


@app.cell
def _(mo) -> None:
    mo.md(
        r"""
    # SMS Interactive Simulation Interface
    Welcome to **SMS (Simulating Microbial Systems)**, a browser-based interface for running and
    analyzing whole-cell *E. coli* simulations. This notebook is powered
    by [Marimo](https://github.com/marimo-team/marimo) and provides lightweight
    access to *E. coli* models relevant to microbial dynamics, biomanufacturing,
    and antibiotic response.

    Use the controls in each section to interact with data.
    """
    )
    return


@app.cell
def _() -> tuple:
    import marimo as mo
    import numpy as np

    return mo, np


@app.cell
def _(mo) -> None:
    mo.md(
        r"""
    ## Experiment Configuration

    This section focuses on the configuration/parameterization of **SMS Ecoli Experiments**.
    Use this to any or all of the following:

    - Specify partitioning requests (n_generations, n_init_sims, etc)
    - Specify multivariant simulations
    - Configure pre-simulation parameter calculation
    - Configure post-simulation analyses
    
    For example, consider a user that has created new Ecoli variants, along with corresponding analyses which
    compare strain variants under different feeding strategies. The user may use this notebook to create a 
    simulation experiment configuration that, when used to parameterize an SMS API simulation request:
    a.) runs the base parameter calculation, b.) instantiates the variants as specified by the config,
    c.) runs a multivariant simulation, and d.) runs the aforementioned post-processing. **This notebook
    is under active development and is expected to change without notice; we've been busy :) **
    """
    )
    return


if __name__ == "__main__":
    app.run()
