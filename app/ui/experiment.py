import marimo

__generated_with = "0.14.17"
app = marimo.App(width="full", layout_file="layouts/experiment.grid.json")


@app.cell
def _():
    import httpx
    import asyncio
    import marimo as mo

    return asyncio, httpx, mo


@app.cell
def _(mo):
    getSim, setSim = mo.state(None)
    getLog, setLog = mo.state(None)
    getSimId, setSimId = mo.state(None)
    getStatus, setStatus = mo.state({"id": None, "status": "waiting"})

    getAnalysis, setAnalysis = mo.state(None)
    getAnalysisStatus, setAnalysisStatus = mo.state(None)
    return (
        getLog,
        getSim,
        getSimId,
        getStatus,
        setLog,
        setSim,
        setSimId,
        setStatus,
    )


@app.cell
def _(httpx):
    async def fetch_sim_status(id: int):
        url = f"http://localhost:8888/v1/ecoli/simulations/{id}/status"
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(url, headers={"accept": "application/json", "Content-Type": "application/json"})
            res.raise_for_status()
            return res.json()

    async def fetch_sim_log(id: int):
        url = f"http://localhost:8888/v1/ecoli/simulations/{id}/log"
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers={"accept": "text/plain"})
            res.raise_for_status()
            log_text = res.text  # <--- raw string with real line breaks
            # print(log_text)
            return log_text

    async def run_sim(payload=None):
        url = "http://localhost:8888/v1/ecoli/simulations"
        payload = payload or {
            "request": {
                "experiment_id": "smsapi-e8f5f96c96fe8707_1758726725233-9cce83075f1e7681_1758726725234",
                "simulation_name": "smsapi-e8f5f96c96fe8707_1758726725233",
                "metadata": {},
                "run_parca": True,
                "generations": 1,
                "max_duration": 10800,
                "initial_global_time": 0,
                "time_step": 1,
                "single_daughters": True,
                "variants": {},
                "analysis_options": {},
                "division_variable": [],
                "add_processes": [],
                "exclude_processes": [],
                "processes": [],
                "process_configs": {},
                "topology": {},
                "engine_process_reports": [],
                "emit_paths": [],
                "inherit_from": [],
                "spatial_environment_config": {},
                "swap_processes": {},
                "flow": {},
                "initial_state_overrides": [],
                "initial_state": {},
            },
            "metadata": {"additionalProp1": "string", "additionalProp2": "string", "additionalProp3": "string"},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                timeout=30,
                json=payload,
                headers={"accept": "application/json", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            print(data)
            return data

    return fetch_sim_log, fetch_sim_status, run_sim


@app.cell
def _(mo):
    run_btn = mo.ui.run_button(label="Run", kind="success")
    refresh_btn = mo.ui.run_button(label="Refresh", kind="info")
    return refresh_btn, run_btn


@app.cell
async def _(
    asyncio,
    fetch_sim_log,
    fetch_sim_status,
    getSimId,
    refresh_btn,
    setLog,
    setStatus,
):
    if refresh_btn.value:
        await asyncio.sleep(2)
        dbId = getSimId()

        log = await fetch_sim_log(dbId)
        setLog(log)

        status = await fetch_sim_status(dbId)
        setStatus(status)
    return


@app.cell
async def _(collect_config, run_btn, run_sim, setSim, setSimId):
    if run_btn.value:
        payload = {"request": collect_config(), "metadata": {"context": "ui"}}
        exp = await run_sim()
        setSim(exp)
        setSimId(exp["database_id"])
    return


@app.cell
def _(getLog, getStatus, mo):
    logg = getLog()
    statuss = getStatus()
    log_panel = mo.ui.text_area(value=logg or "", label="Simulation Log", disabled=True).callout(
        kind="success" if logg is not None else "info"
    )
    status_panel = mo.ui.text_area(value=statuss["status"] or "", label="Simulation Status", disabled=True).callout(
        kind="success" if logg is not None else "info"
    )
    return log_panel, logg, status_panel, statuss


@app.cell
def _(mo):
    simconfig = mo.ui.dictionary(
        {
            "experiment_id": mo.ui.text(value="'<ID>'"),
            "simulation_name": mo.ui.text(value="'<ID>'"),
            "metadata": mo.ui.text_area(value="{}"),
            "run_parca": mo.ui.text_area(value="True"),
            "generations": mo.ui.number(start=1, stop=1111, value=1),
            "max_duration": mo.ui.number(start=1000, stop=11000, value=10800),
            "variants": mo.ui.text_area(value="{}"),
            "analysis_options": mo.ui.text_area(value="{}"),
            "division_variable": mo.ui.text_area(value="[]"),
            "add_processes": mo.ui.text_area(value="[]"),
            "exclude_processes": mo.ui.text_area(value="[]"),
            "processes": mo.ui.text_area(value="[]"),
            "process_configs": mo.ui.text_area(value="{}"),
            "topology": mo.ui.text_area(value="{}"),
            "engine_process_reports": mo.ui.text_area(value="[]"),
            "emit_paths": mo.ui.text_area(value="[]"),
            "inherit_from": mo.ui.text_area(value="[]"),
            "spatial_environment_config": mo.ui.text_area(value="{}"),
            "swap_processes": mo.ui.text_area(value="{}"),
            "flow": mo.ui.text_area(value="{}"),
            "initial_state_overrides": mo.ui.text_area(value="[]"),
            "initial_state": mo.ui.text_area(value="{}"),
        },
        label="Simulation Configuration: ",
    )
    simconfig
    return (simconfig,)


@app.cell
def _(mo):
    def render_analysis_config():
        analysis_scopes = ["single", "multigeneration", "multiseed"]
        ptools_modnames = [f"ptools_{val}" for val in ["rxns", "rna", "proteins"]]

        analysis_conf = {
            "experiment_id": mo.ui.text(value="sms_multigeneration"),
            "analysis_name": mo.ui.text(value="ptools_test_2"),
        }
        for scope in analysis_scopes:
            analysis_conf[scope] = mo.ui.dictionary(
                {
                    modname: mo.ui.dictionary({"n_tp": mo.ui.number(value=8)}, label=f"{modname} parameters")
                    for modname in ptools_modnames
                },
                label=f"{scope} anaylsis config",
            )
        return mo.ui.dictionary(analysis_conf, label="Analysis Configuration")

    analysis_config = render_analysis_config()
    analysis_config
    return (analysis_config,)


@app.cell
def _(mo):
    interaction_mode_dd = mo.ui.dropdown(
        label="Interaction Mode: ", options=["Simulation", "Analysis"], value="Analysis"
    )
    interaction_mode_dd
    return (interaction_mode_dd,)


@app.cell
def _(interaction_mode_dd):
    interaction_mode_dd.value
    return


@app.cell
def _(analysis_config, interaction_mode_dd, mo, simconfig):
    def onchange():
        raise ValueError("Cannot change")

    mo.ui.tabs(
        {"Simulation": simconfig, "Analysis": analysis_config},
        label="Choose Simulation Type",
        value=interaction_mode_dd.value,
        on_change=lambda _: onchange(),
    )
    return


@app.cell
def _(simconfig):
    def collect_config():
        vals = {}
        for k, val in simconfig.value.items():
            print(k, val)
            try:
                vals[k] = eval(val)
            except:
                vals[k] = val
            # vals[k] = eval(val)

        return vals

    return (collect_config,)


@app.cell
def _(getSim):
    expp = getSim()
    print(expp) if expp is not None else print()
    return (expp,)


@app.cell
def _(status_panel):
    status_panel
    return


@app.cell
def _(refresh_btn):
    refresh_btn
    return


@app.cell
def _(run_btn):
    run_btn
    return


@app.cell
def _(log_panel):
    log_panel
    return


@app.cell
def _(expp, logg, mo, statuss):
    md = None
    if logg is not None:
        md = mo.md(f"""
            **Name**: ```{expp.get("name")}```

            **Simulation ID**: ```{statuss.get("id")}```

            **Status**: ```{statuss.get("status")}```

            **Log**:

            {logg}
        """)
    md
    return


@app.cell
def _(logg):
    logg
    return


@app.cell
def _(logg, mo):
    mo.ui.text_area(value=logg or "", label="Simulation Log", disabled=True).batch()
    return


@app.cell
def _(logg):
    print(logg) if logg is not None else print()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
