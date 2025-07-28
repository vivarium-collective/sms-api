import marimo

__generated_with = "0.14.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import json 

    import orjson
    import httpx
    import marimo as mo 
    import polars as pl 

    def get_data_size(X: bytes) -> float:
        n_bytes = len(X)
        return n_bytes / (1024 * 1024)
    return httpx, json, mo, orjson, pl


@app.cell
def _(mo):
    get_results, set_results = mo.state(None)
    return get_results, set_results


@app.cell
def _(httpx, json, orjson, pl, set_results):
    async def on_get_results(selected_observables: list[str] | None = None):
        url = "http://localhost:8888/core/simulation/run/results"
        headers = {
            "Content-Type": "application/json",
            "accept": "*/*"
        }
        data = json.dumps(selected_observables) if selected_observables else None 
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(130.0)) as client:
                resp = await client.post(
                    url=url,
                    headers=headers, 
                    data=data
                )
                resp.raise_for_status()
            set_results(
                pl.LazyFrame(
                    orjson.loads(resp.json())
                ).collect()
            )
        except:
            raise Exception("Something went wrong!")
    return (on_get_results,)


@app.cell
def _():
    # set number of requested observables
    # get_num_obs, set_num_obs = mo.state(0)
    return


@app.cell
def _():
    # add_obs_btn = mo.ui.run_button(label="+", on_change=lambda _: set_num_obs(get_num_obs() + 1))
    # rm_obs_btn = mo.ui.run_button(label="-", on_change=lambda _: set_num_obs(get_num_obs() - 1))
    # observable = mo.ui.text(placeholder="Observable Name")
    return


@app.cell
def _():
    # selected = [observable] * get_num_obs()
    return


@app.cell
def _():
    # observables = mo.ui.array(selected, label="Selected Observables")
    # mo.hstack([observables, add_obs_btn, rm_obs_btn], justify="start")
    return


@app.cell
def _():
    # data = json.dumps(observables.value) if observables.value else None
    return


@app.cell
def _(json):
    url = "http://localhost:8888/core/simulation/run/results"
    headers = {
        "Content-Type": "application/json",
        "accept": "*/*"
    }
    selected_observables = ["time", "listeners__mass__cell_mass"]
    data = json.dumps(selected_observables)
    return (selected_observables,)


@app.cell
def _(mo):
    plot = mo.ui.run_button(label=f"{mo.icon('carbon:qq-plot')}")
    plot
    return (plot,)


@app.cell
async def _(on_get_results, plot, selected_observables):
    if plot.value:
        await on_get_results(selected_observables)
    return


@app.cell
def _(get_results):
    results = get_results()
    return (results,)


@app.cell
def _(pl, results):
    df = pl.DataFrame(results)
    return (df,)


@app.cell
def _(df, results, selected_observables):
    chart = None 
    if results is not None:
        xaxis, yaxis = selected_observables
        chart = df.plot.line(x=xaxis, y=yaxis)
    chart
    return


@app.cell
def _(results):
    results
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
