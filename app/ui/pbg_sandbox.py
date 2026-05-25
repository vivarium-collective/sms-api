import marimo

__generated_with = "0.23.0"
app = marimo.App(width="full", title="PBG Live Sandbox — sms-api")


@app.cell
def _():
    import marimo as mo
    import httpx
    import json as _json

    BASE = "https://sms.cam.uchc.edu"

    # Processes in the link_registry — verified via GET /compose/v1/process/{name}/config-schema
    # on sms-api-rke v0.9.3. All config_schema data sourced from the live API.
    REGISTRY = [
        {
            "name": "MSEComparison",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": False,
            "config_schema": {"ignore_nans": "boolean", "columns_of_interest": "list[string]"},
            "default_config": {"ignore_nans": False, "columns_of_interest": []},
        },
        {
            "name": "ComparisonTool",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": False,
            "config_schema": {"ignore_nans": "boolean", "columns_of_interest": "list[string]"},
            "default_config": {"ignore_nans": False, "columns_of_interest": []},
        },
        {
            "name": "CopasiUTCStep",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": True,
            "config_schema": {"model_source": "string", "time": "float", "n_points": "integer", "output_dir": "string"},
            "default_config": {"model_source": "", "time": 1.0, "n_points": 100, "output_dir": "/tmp"},
        },
        {
            "name": "CopasiUTCProcess",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": True,
            "config_schema": {"model_source": "string", "time": "float", "intervals": "integer"},
            "default_config": {"model_source": "", "time": 1.0, "intervals": 10},
        },
        {
            "name": "CopasiSteadyStateStep",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": True,
            "config_schema": {"model_source": "string", "time": "float"},
            "default_config": {"model_source": "", "time": 1.0},
        },
        {
            "name": "TelluriumUTCStep",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": True,
            "config_schema": {"model_source": "string", "time": "float", "n_points": "integer", "output_dir": "string"},
            "default_config": {"model_source": "", "time": 1.0, "n_points": 100, "output_dir": "/tmp"},
        },
        {
            "name": "TelluriumSteadyStateStep",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": True,
            "config_schema": {"model_source": "string"},
            "default_config": {"model_source": ""},
        },
        {
            "name": "TelluriumStep",
            "pkg": "pbsim_common",
            "category": "link_registry",
            "requires_sbml": False,
            "config_schema": {},
            "default_config": {},
        },
        {
            "name": "Step",
            "pkg": "process_bigraph",
            "category": "link_registry",
            "requires_sbml": False,
            "config_schema": {},
            "default_config": {},
        },
        {
            "name": "Process",
            "pkg": "process_bigraph",
            "category": "link_registry",
            "requires_sbml": False,
            "config_schema": {},
            "default_config": {},
        },
        {
            "name": "edge",
            "pkg": "bigraph_schema",
            "category": "link_registry",
            "requires_sbml": False,
            "config_schema": {},
            "default_config": {},
        },
    ]

    return BASE, REGISTRY, _json, httpx, mo


@app.cell
def _(BASE, REGISTRY, httpx, mo):
    try:
        _r = httpx.get(f"{BASE}/compose/v1/types", timeout=10)
        _live_types = _r.json() if _r.status_code == 200 else []
        _n_types = len(_live_types)
        _conn = "🟢 Connected"
    except Exception:
        _n_types = "?"
        _conn = "🔴 Unreachable"

    mo.md(f"""
    <div style="background:#1a1a2e;border:1px solid #2d2d50;border-radius:12px;padding:28px 32px;margin-bottom:24px;">
    <div style="font-size:11px;letter-spacing:2px;color:#818cf8;text-transform:uppercase;margin-bottom:8px;">sms-api · process-bigraph</div>
    <h1 style="font-size:28px;font-weight:700;color:#e2e8f0;margin:0 0 8px;">⚗️ PBG Live Sandbox</h1>
    <p style="color:#94a3b8;font-size:14px;margin:0 0 16px;">
      All operations call <code style="background:#222240;padding:2px 6px;border-radius:4px;color:#818cf8">{BASE}</code> directly.
      No local process-bigraph installation required.
    </p>
    <div style="display:flex;gap:20px;font-size:12px;color:#94a3b8;flex-wrap:wrap;">
      <span>{_conn} to sms-api-rke v0.9.3</span>
      <span>·</span>
      <span><b style="color:#e2e8f0">{len(REGISTRY)}</b> link_registry processes</span>
      <span>·</span>
      <span><b style="color:#e2e8f0">{_n_types}</b> bigraph-schema types</span>
      <span>·</span>
      <span><b style="color:#e2e8f0">1</b> v2ecoli curated composite</span>
    </div>
    </div>
    """)
    return


@app.cell
def _(mo):
    # ── Process Runtime state ────────────────────────────────────────────────────
    get_pid, set_pid = mo.state(None)
    get_proc_inputs, set_proc_inputs = mo.state(None)
    get_proc_outputs, set_proc_outputs = mo.state(None)
    get_init_error, set_init_error = mo.state(None)
    return (
        get_init_error,
        get_pid,
        get_proc_inputs,
        get_proc_outputs,
        set_init_error,
        set_pid,
        set_proc_inputs,
        set_proc_outputs,
    )


@app.cell
def _(mo):
    # ── BioModels state ──────────────────────────────────────────────────────────
    get_bio_ids, set_bio_ids = mo.state(None)
    get_bio_meta, set_bio_meta = mo.state(None)
    get_bio_sim_id, set_bio_sim_id = mo.state(None)
    get_bio_error, set_bio_error = mo.state(None)
    return (
        get_bio_error,
        get_bio_ids,
        get_bio_meta,
        get_bio_sim_id,
        set_bio_error,
        set_bio_ids,
        set_bio_meta,
        set_bio_sim_id,
    )


@app.cell
def _(mo):
    # ── v2ecoli state ────────────────────────────────────────────────────────────
    get_ecoli_sim_id, set_ecoli_sim_id = mo.state(None)
    get_ecoli_error, set_ecoli_error = mo.state(None)
    return get_ecoli_error, get_ecoli_sim_id, set_ecoli_error, set_ecoli_sim_id


@app.cell
def _(REGISTRY, mo):
    # ── Process Runtime controls ─────────────────────────────────────────────────
    proc_select = mo.ui.dropdown(
        options=[r["name"] for r in REGISTRY],
        value="MSEComparison",
        label="Process",
    )
    init_btn = mo.ui.button(label="Initialize →", kind="success")
    end_btn = mo.ui.button(label="End Process", kind="danger")
    return end_btn, init_btn, proc_select


@app.cell
def _(REGISTRY, _json, mo, proc_select):
    # Config editor — resets to default when process changes
    _entry = next((r for r in REGISTRY if r["name"] == proc_select.value), {})
    _default = _json.dumps(_entry.get("default_config", {}), indent=2)
    _sbml_warn = (
        mo.callout(
            mo.md(
                "**Requires SBML** — `model_source` must be a valid path on the HPC filesystem. "
                "Use `POST /compose/v1/biomodels/{id}/run` or `POST /compose/v1/curated/copasi` "
                "for full SBML-backed runs."
            ),
            kind="warn",
        )
        if _entry.get("requires_sbml")
        else mo.md("")
    )
    config_editor = mo.ui.text_area(value=_default, label="Config (JSON)", rows=5)
    return _sbml_warn, config_editor


@app.cell
def _(
    BASE,
    _json,
    config_editor,
    httpx,
    init_btn,
    mo,
    proc_select,
    set_init_error,
    set_pid,
    set_proc_inputs,
    set_proc_outputs,
):
    # ── Initialize action ────────────────────────────────────────────────────────
    mo.stop(init_btn.value == 0)
    _name = proc_select.value
    try:
        _cfg = _json.loads(config_editor.value)
        _r = httpx.post(
            f"{BASE}/compose/v1/process/{_name}/initialize",
            json={"config": _cfg},
            timeout=15,
        )
        if _r.status_code == 200:
            _pid = _r.json()["process_id"]
            set_pid(_pid)
            set_init_error(None)
            _ir = httpx.get(f"{BASE}/compose/v1/process/{_name}/inputs/{_pid}", timeout=10)
            _or = httpx.get(f"{BASE}/compose/v1/process/{_name}/outputs/{_pid}", timeout=10)
            set_proc_inputs(_ir.json() if _ir.status_code == 200 else {})
            set_proc_outputs(_or.json() if _or.status_code == 200 else {})
        else:
            set_pid(None)
            set_init_error(f"HTTP {_r.status_code}: {_r.text}")
    except Exception as _e:
        set_pid(None)
        set_init_error(str(_e))
    return


@app.cell
def _(BASE, end_btn, get_pid, httpx, mo, proc_select, set_pid, set_proc_inputs, set_proc_outputs):
    # ── End action ───────────────────────────────────────────────────────────────
    mo.stop(end_btn.value == 0 or get_pid() is None)
    _r = httpx.post(f"{BASE}/compose/v1/process/{proc_select.value}/end/{get_pid()}", timeout=10)
    if _r.status_code == 200:
        set_pid(None)
        set_proc_inputs(None)
        set_proc_outputs(None)
    return


@app.cell
def _(mo):
    # ── BioModels controls ───────────────────────────────────────────────────────
    biomodel_id_input = mo.ui.text(value="BIOMD0000000001", label="BioModel ID")
    bio_n_slider = mo.ui.slider(start=1, stop=100, value=5, label="Number of IDs to fetch")
    fetch_ids_btn = mo.ui.button(label="Fetch IDs from EBI")
    fetch_meta_btn = mo.ui.button(label="Get Metadata")
    bio_sim_select = mo.ui.dropdown(options=["copasi", "tellurium"], value="copasi", label="Simulator")
    bio_run_btn = mo.ui.button(label="Submit Run → SLURM", kind="warn")
    return (
        bio_n_slider,
        bio_run_btn,
        bio_sim_select,
        biomodel_id_input,
        fetch_ids_btn,
        fetch_meta_btn,
    )


@app.cell
def _(BASE, bio_n_slider, fetch_ids_btn, httpx, mo, set_bio_error, set_bio_ids):
    mo.stop(fetch_ids_btn.value == 0)
    try:
        _r = httpx.get(f"{BASE}/compose/v1/biomodels/identifiers", params={"n": bio_n_slider.value}, timeout=15)
        if _r.status_code == 200:
            set_bio_ids(_r.json())
            set_bio_error(None)
        else:
            set_bio_error(f"HTTP {_r.status_code}: {_r.text}")
    except Exception as _e:
        set_bio_error(str(_e))
    return


@app.cell
def _(BASE, biomodel_id_input, fetch_meta_btn, httpx, mo, set_bio_error, set_bio_meta):
    mo.stop(fetch_meta_btn.value == 0)
    try:
        _r = httpx.get(
            f"{BASE}/compose/v1/biomodels/{biomodel_id_input.value}/metadata",
            timeout=15,
        )
        if _r.status_code == 200:
            set_bio_meta(_r.json())
            set_bio_error(None)
        else:
            set_bio_error(f"HTTP {_r.status_code}: {_r.text}")
    except Exception as _e:
        set_bio_error(str(_e))
    return


@app.cell
def _(
    BASE,
    bio_run_btn,
    bio_sim_select,
    biomodel_id_input,
    httpx,
    mo,
    set_bio_error,
    set_bio_sim_id,
):
    mo.stop(bio_run_btn.value == 0)
    try:
        _r = httpx.post(
            f"{BASE}/compose/v1/biomodels/{biomodel_id_input.value}/run",
            params={"simulator": bio_sim_select.value},
            timeout=30,
        )
        if _r.status_code == 200:
            set_bio_sim_id(_r.json())
            set_bio_error(None)
        else:
            set_bio_error(f"HTTP {_r.status_code}: {_r.text}")
    except Exception as _e:
        set_bio_error(str(_e))
    return


@app.cell
def _(mo):
    # ── v2ecoli controls ─────────────────────────────────────────────────────────
    ecoli_duration = mo.ui.slider(start=5, stop=120, value=10, step=5, label="Duration (seconds biological time)")
    ecoli_seed = mo.ui.number(start=0, stop=9999, value=0, label="Random seed")
    ecoli_interval = mo.ui.slider(start=0.1, stop=5.0, value=1.0, step=0.1, label="Interval (seconds)")
    ecoli_run_btn = mo.ui.button(label="Submit v2ecoli → SLURM", kind="warn")
    return ecoli_duration, ecoli_interval, ecoli_run_btn, ecoli_seed


@app.cell
def _(
    BASE,
    ecoli_duration,
    ecoli_interval,
    ecoli_run_btn,
    ecoli_seed,
    httpx,
    mo,
    set_ecoli_error,
    set_ecoli_sim_id,
):
    mo.stop(ecoli_run_btn.value == 0)
    try:
        _r = httpx.post(
            f"{BASE}/compose/v1/curated/ecoli",
            params={
                "duration": ecoli_duration.value,
                "seed": int(ecoli_seed.value),
                "interval": ecoli_interval.value,
                "features": "[]",
            },
            timeout=30,
        )
        if _r.status_code == 200:
            set_ecoli_sim_id(_r.json())
            set_ecoli_error(None)
        else:
            set_ecoli_error(f"HTTP {_r.status_code}: {_r.text}")
    except Exception as _e:
        set_ecoli_error(str(_e))
    return


@app.cell
def _(BASE, httpx, mo):
    # ── Type browser — fetched live ──────────────────────────────────────────────
    try:
        _r = httpx.get(f"{BASE}/compose/v1/types", timeout=10)
        _types = _r.json() if _r.status_code == 200 else []
    except Exception:
        _types = []

    _type_rows = [{"type": t} for t in _types]
    _type_table = (
        mo.ui.table(_type_rows, label="Bigraph-schema types (live)") if _type_rows else mo.md("Could not fetch types.")
    )
    return (_type_table,)


@app.cell
def _(
    BASE,
    REGISTRY,
    _json,
    _sbml_warn,
    _type_table,
    bio_n_slider,
    bio_run_btn,
    bio_sim_select,
    biomodel_id_input,
    config_editor,
    ecoli_duration,
    ecoli_interval,
    ecoli_run_btn,
    ecoli_seed,
    end_btn,
    fetch_ids_btn,
    fetch_meta_btn,
    get_bio_error,
    get_bio_ids,
    get_bio_meta,
    get_bio_sim_id,
    get_ecoli_error,
    get_ecoli_sim_id,
    get_init_error,
    get_pid,
    get_proc_inputs,
    get_proc_outputs,
    init_btn,
    mo,
    proc_select,
):
    # ── Process Runtime display ──────────────────────────────────────────────────
    _entry = next((r for r in REGISTRY if r["name"] == proc_select.value), {})
    _schema_rows = [{"field": k, "type": v} for k, v in _entry.get("config_schema", {}).items()]
    _schema_display = (
        mo.ui.table(_schema_rows, label="config_schema (from live API)")
        if _schema_rows
        else mo.md("*No config required.*")
    )

    _pid = get_pid()
    _status_color = "#10b981" if _pid else "#94a3b8"
    _status_text = f"Active: `{_pid}`" if _pid else "No active instance"

    _inputs_display = mo.md("")
    _outputs_display = mo.md("")
    if _pid and get_proc_inputs() is not None:
        _inputs_display = (
            mo.ui.table(
                [{"field": k, "type": v} for k, v in get_proc_inputs().items()],
                label="inputs",
            )
            if get_proc_inputs()
            else mo.md("*No inputs.*")
        )
        _outputs_display = (
            mo.ui.table(
                [{"field": k, "type": v} for k, v in get_proc_outputs().items()],
                label="outputs",
            )
            if get_proc_outputs()
            else mo.md("*No outputs.*")
        )

    _init_error_display = (
        mo.callout(mo.md(f"**Error:** {get_init_error()}"), kind="danger") if get_init_error() else mo.md("")
    )

    _proc_tab = mo.vstack([
        mo.md(
            "### Process Runtime Sandbox\nAll calls go to `POST /compose/v1/process/{name}/initialize` → inputs → outputs → end. "
            "**MSEComparison** and **ComparisonTool** work immediately (no SBML). "
            "SBML-requiring processes need a model file on the HPC filesystem."
        ),
        mo.hstack([proc_select, init_btn, end_btn], justify="start"),
        _sbml_warn,
        mo.hstack([
            mo.vstack([mo.md("**config_schema**"), _schema_display]),
            mo.vstack([config_editor]),
        ]),
        mo.md(f"**Status:** <span style='color:{_status_color}'>{_status_text}</span>"),
        _init_error_display,
        _inputs_display,
        _outputs_display,
    ])

    # ── BioModels display ────────────────────────────────────────────────────────
    _bio_ids_display = mo.md("")
    _bio_meta_display = mo.md("")
    _bio_sim_display = mo.md("")
    _bio_err_display = (
        mo.callout(mo.md(f"**Error:** {get_bio_error()}"), kind="danger") if get_bio_error() else mo.md("")
    )

    if get_bio_ids():
        _bio_ids_display = mo.ui.table([{"biomodel_id": i} for i in get_bio_ids()], label="EBI identifiers")
    if get_bio_meta():
        _m = get_bio_meta()
        _files = _m.get("metadata", {}).get("files", [])
        _bio_meta_display = mo.vstack([
            mo.md(f"**{_m.get('biomodel_id', '')}** — {len(_files)} files from EBI"),
            mo.ui.table(_files, label="Files") if _files else mo.md(""),
        ])
    if get_bio_sim_id():
        _bio_sim_display = mo.callout(
            mo.md(
                f"**Submitted!** Simulation record:\n```json\n{_json.dumps(get_bio_sim_id(), indent=2)}\n```\n\n"
                f"Poll status: `atlantis compose status <id> --base-url {BASE}`"
            ),
            kind="success",
        )

    _bio_tab = mo.vstack([
        mo.md(
            "### BioModels Explorer\nFetch model IDs from EBI, inspect metadata, and dispatch SLURM simulation jobs "
            "via `POST /compose/v1/biomodels/{id}/run`. Calls EBI BioModels REST API server-side."
        ),
        mo.hstack([bio_n_slider, fetch_ids_btn], justify="start"),
        _bio_ids_display,
        mo.md("---"),
        mo.hstack([biomodel_id_input, fetch_meta_btn], justify="start"),
        _bio_meta_display,
        mo.md("---"),
        mo.hstack([bio_sim_select, bio_run_btn], justify="start"),
        _bio_sim_display,
        _bio_err_display,
    ])

    # ── v2ecoli display ──────────────────────────────────────────────────────────
    _ecoli_display = mo.md("")
    _ecoli_err_display = (
        mo.callout(mo.md(f"**Error:** {get_ecoli_error()}"), kind="danger") if get_ecoli_error() else mo.md("")
    )

    if get_ecoli_sim_id():
        _ecoli_display = mo.callout(
            mo.md(
                f"**Submitted!** v2ecoli SLURM job dispatched:\n```json\n{_json.dumps(get_ecoli_sim_id(), indent=2)}\n```\n\n"
                f"Poll status: `atlantis compose status <id> --base-url {BASE}`"
            ),
            kind="success",
        )

    _ecoli_tab = mo.vstack([
        mo.md(
            "### v2ecoli Whole-Cell Simulator\nDispatches a whole-cell *E. coli* simulation via "
            "`POST /compose/v1/curated/ecoli`. The API builds a process-bigraph Composite document "
            "wiring **~55 biological processes** (transcription, translation, metabolism, replication, …) "
            "and runs them in a Singularity container on UCONN CCAM SLURM. No SBML required — "
            "the biological model is pre-computed in the ParCa cache."
        ),
        mo.callout(
            mo.md(
                "**Note:** Submissions run on HPC. Typical duration: 5–30 min wall-clock for 10–60s biological time."
            ),
            kind="info",
        ),
        ecoli_duration,
        mo.hstack([ecoli_seed, ecoli_interval], justify="start"),
        ecoli_run_btn,
        _ecoli_display,
        _ecoli_err_display,
    ])

    # ── Registry display ─────────────────────────────────────────────────────────
    _reg_rows = [
        {
            "name": r["name"],
            "package": r["pkg"],
            "category": r["category"],
            "requires_sbml": "yes" if r["requires_sbml"] else "no",
            "config_fields": ", ".join(r["config_schema"].keys()) or "—",
        }
        for r in REGISTRY
    ]
    _reg_tab = mo.vstack([
        mo.md(
            "### Live Registry\nAll 11 link_registry processes verified via "
            "`GET /compose/v1/process/{name}/config-schema` on sms-api-rke v0.9.3. "
            "Plus **v2ecoli** curated composite (`POST /compose/v1/curated/ecoli`)."
        ),
        mo.ui.table(_reg_rows, label="link_registry — addressable via process runtime endpoints"),
    ])

    # ── Type browser ─────────────────────────────────────────────────────────────
    _type_tab = mo.vstack([
        mo.md(
            "### Bigraph-Schema Types\nFetched live from `GET /compose/v1/types`. "
            "These are the 42 primitive types used in all `config_schema`, `inputs`, and `outputs` definitions."
        ),
        _type_table,
    ])

    # ── Assemble tabs ────────────────────────────────────────────────────────────
    mo.ui.tabs({
        "⚗️ Process Runtime": _proc_tab,
        "🧬 BioModels": _bio_tab,
        "🦠 v2ecoli": _ecoli_tab,
        "📋 Registry": _reg_tab,
        "🔷 Types": _type_tab,
    })
    return


if __name__ == "__main__":
    app.run()
