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
def _():
    import marimo as mo
    import numpy as np

    return mo, np


@app.cell
def _(mo):
    mo.md(
        r"""
    ## Antibiotics

    Simulate the effects of the antibiotic mecillinam on *E. coli* populations.
    """
    )
    return


if __name__ == "__main__":
    app.run()
