import marimo

__generated_with = "0.14.17"
app = marimo.App(width="full", layout_file="layouts/vecoli.grid.json")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.ui.run_button(kind="success")

    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
