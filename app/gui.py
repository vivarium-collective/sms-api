import marimo

__generated_with = "0.22.4"
app = marimo.App(width="medium", layout_file="layouts/gui_app.grid.json")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import json
    import time
    import traceback
    from pathlib import Path

    return Path, json, time, traceback


@app.cell
def _(mo):
    # Memphis Group (early-90s) inspired color constants
    MAGENTA = "#e91e90"
    CYAN = "#00e5ff"
    YELLOW = "#ffe100"
    GREEN = "#39ff14"
    RED = "#ff3131"
    CORAL = "#ff6f61"
    PURPLE = "#b388ff"
    TEAL = "#00bfa5"
    BG_DARK = "#1a1a2e"
    BG_CARD = "#16213e"
    TEXT_LIGHT = "#e0e0e0"
    BORDER_GLOW = MAGENTA

    # Inject a global stylesheet with Memphis accents
    _memphis_css = mo.Html(f"""<style>
    :root {{
        --memphis-magenta: {MAGENTA};
        --memphis-cyan: {CYAN};
        --memphis-yellow: {YELLOW};
        --memphis-green: {GREEN};
        --memphis-red: {RED};
        --memphis-purple: {PURPLE};
        --memphis-bg: {BG_DARK};
        --memphis-card: {BG_CARD};
    }}
    .memphis-banner {{
        background: linear-gradient(90deg, {MAGENTA}, {CYAN}, {YELLOW}, {MAGENTA});
        background-size: 300% 100%;
        animation: memphis-scroll 8s linear infinite;
        height: 6px;
        border-radius: 3px;
        margin: 0 0 1.2rem 0;
    }}
    @keyframes memphis-scroll {{
        0% {{ background-position: 0% 50%; }}
        100% {{ background-position: 300% 50%; }}
    }}
    .memphis-title {{
        font-family: 'Courier New', monospace;
        font-weight: 900;
        font-size: 1.6rem;
        background: linear-gradient(90deg, {MAGENTA}, {CYAN});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 0.08em;
    }}
    .memphis-subtitle {{
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        color: {CYAN};
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }}
    .memphis-card {{
        border: 1px solid {MAGENTA}40;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }}
    .memphis-status-completed {{ color: {GREEN}; font-weight: bold; }}
    .memphis-status-running {{ color: {YELLOW}; font-weight: bold; }}
    .memphis-status-failed {{ color: {RED}; font-weight: bold; }}
    .memphis-status-pending {{ color: {CYAN}; font-weight: bold; }}
    .memphis-status-cancelled {{ color: {CORAL}; font-weight: bold; }}
    .memphis-status-unknown {{ color: {PURPLE}; font-weight: bold; }}
    .memphis-accent {{
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }}
    .memphis-dot-magenta {{ background: {MAGENTA}; }}
    .memphis-dot-cyan {{ background: {CYAN}; }}
    .memphis-dot-yellow {{ background: {YELLOW}; }}
    </style>""")
    _memphis_css
    return CYAN, MAGENTA


@app.cell
def _(mo):
    # Thematic iconify icons — bio-sci Memphis Atlantis device aesthetic
    ICO_DNA = mo.icon("twemoji:dna", size=18)
    ICO_DNA_SM = mo.icon("twemoji:dna", size=14)
    ICO_MICROBE = mo.icon("twemoji:microbe", size=18)
    ICO_MICROSCOPE = mo.icon("twemoji:microscope", size=20)
    ICO_TEST_TUBE = mo.icon("twemoji:test-tube", size=20)
    ICO_PETRI_DISH = mo.icon("twemoji:petri-dish", size=20)
    ICO_BAR_CHART = mo.icon("twemoji:bar-chart", size=20)
    ICO_FILE_FOLDER = mo.icon("twemoji:open-file-folder", size=20)
    ICO_GEAR = mo.icon("twemoji:gear", size=16)
    ICO_CHECK = mo.icon("twemoji:check-mark-button", size=16)
    ICO_CROSS = mo.icon("twemoji:cross-mark", size=16)
    ICO_ROCKET = mo.icon("twemoji:rocket", size=16)
    ICO_HOURGLASS = mo.icon("twemoji:hourglass-not-done", size=16)
    ICO_STOP = mo.icon("twemoji:stop-sign", size=16)
    ICO_DOWN_ARROW = mo.icon("twemoji:down-arrow", size=16)
    ICO_LINK = mo.icon("twemoji:link", size=14)
    return (
        ICO_CHECK,
        ICO_CROSS,
        ICO_DNA,
        ICO_DNA_SM,
        ICO_DOWN_ARROW,
        ICO_FILE_FOLDER,
        ICO_GEAR,
        ICO_HOURGLASS,
        ICO_LINK,
        ICO_MICROBE,
        ICO_MICROSCOPE,
        ICO_ROCKET,
        ICO_STOP,
        ICO_TEST_TUBE,
    )


@app.cell
def _(ICO_CHECK, ICO_CROSS, ICO_HOURGLASS, ICO_ROCKET, ICO_STOP, mo):
    def status_badge(status: str) -> "mo.Html":
        """Return an HTML badge with a thematic icon for a given job status."""
        _css_class = f"memphis-status-{status}" if status else "memphis-status-unknown"
        _icon = {
            "completed": ICO_CHECK.text,
            "running": ICO_ROCKET.text,
            "failed": ICO_CROSS.text,
            "pending": ICO_HOURGLASS.text,
            "cancelled": ICO_STOP.text,
        }.get(status, "")
        return mo.Html(f'{_icon} <span class="{_css_class}">{(status or "unknown").upper()}</span>')

    return (status_badge,)


@app.cell
def _(CYAN, ICO_DNA_SM, ICO_MICROBE, MAGENTA, mo):
    _dna = ICO_DNA_SM.text
    _ecoli_art = (
        '<div style="text-align: center;">'
        '<span style="font-family: monospace; font-size: 0.7rem; line-height: 1.3; '
        f'color: {CYAN}; display: inline-block; white-space: pre; text-align: left;">'
        f'<span style="color:#ffd700">  \u256d\u2500</span><span style="color:#008080">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#ff69b4">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#008080">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#ff69b4">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#008080">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#ff69b4">{_dna}</span><span style="color:#ffd700">\u2500\u256e</span>\n'
        f'<span style="color:{MAGENTA}">\u256d\u2500\u256f                              \u2570\u2500\u256e</span>\n'
        f'<span style="color:#00ff00">\u2570\u256e   \u2584\u2580\u2584 \u2580\u2588\u2580 \u2588   \u2584\u2580\u2584 \u2588\u2584 \u2588 \u2580\u2588\u2580 \u2588 \u2584\u2580\u2580  \u256d\u256f~\u223f~\u223f</span>\n'
        f'<span style="color:#9370db"> (   \u2588\u2580\u2588  \u2588  \u2588\u2584\u2584 \u2588\u2580\u2588 \u2588 \u2580\u2588  \u2588  \u2588 \u2584\u2588\u2588  )\u223f~\u223f~</span>\n'
        f'<span style="color:{CYAN}">\u256d\u256f                              \u2570\u256e~\u223f~~\u223f</span>\n'
        f'<span style="color:{MAGENTA}">\u2570\u2500\u256e  \u223f whole-cell simulation \u223f  \u256d\u2500\u256f\u223f~\u223f~</span>\n'
        f'<span style="color:#ffd700">  \u2570\u2500</span><span style="color:#ff69b4">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#008080">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#ff69b4">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#008080">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#ff69b4">{_dna}</span><span style="color:#ffd700">\u2500\u2500</span><span style="color:#008080">{_dna}</span><span style="color:#ffd700">\u2500\u256f</span>'
        "</span></div>"
    )

    _microbe = ICO_MICROBE.text
    mo.Html(
        '<div class="memphis-banner"></div>'
        f"{_ecoli_art}"
        f'<p class="memphis-subtitle" style="margin-top:0.6rem; text-align: center;">'
        f"{_dna} whole-cell simulation platform {_dna} gui client {_microbe}</p>"
        '<div class="memphis-banner" style="margin-top:0.8rem;"></div>'
    )
    return


@app.cell
def _(ICO_GEAR, mo):
    _base_url_options = {
        "Local (8080)": "http://localhost:8080",
        "Local (8888)": "http://localhost:8888",
        "Stanford Forwarded (8080)": "http://localhost:8080",
        "CCAM Prod": "https://sms.cam.uchc.edu",
        "CCAM Dev": "https://sms-dev.cam.uchc.edu",
    }
    base_url_dropdown = mo.ui.dropdown(
        options=_base_url_options,
        value="Local (8080)",
        label=f"{ICO_GEAR.text} API base URL",
    )
    base_url_dropdown
    return (base_url_dropdown,)


@app.cell
def _(base_url_dropdown):
    from app.app_data_service import E2EDataService

    _svc = E2EDataService(base_url=base_url_dropdown.value, timeout=600)

    def get_svc() -> E2EDataService:
        return _svc

    return (get_svc,)


@app.cell(hide_code=True)
def _(ICO_MICROSCOPE, mo):
    mo.md(f"""
    <p class="memphis-title">{ICO_MICROSCOPE.text} Simulator</p>
    """)
    return


@app.cell
def _(ICO_DNA, mo):
    mo.md(f"""
    <p class="memphis-subtitle">{ICO_DNA.text} fetch \u00b7 upload \u00b7 build {ICO_DNA.text}</p>
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    <div class="memphis-banner"></div>
    """)
    return


@app.cell
def _(mo):
    repo_url_input = mo.ui.text(
        value="https://github.com/CovertLabEcoli/vEcoli-private",
        label="Repository URL",
        full_width=True,
    )
    branch_input = mo.ui.text(value="master", label="Branch")
    force_rebuild = mo.ui.checkbox(label="Force rebuild", value=False)

    mo.hstack([repo_url_input, branch_input, force_rebuild], justify="start", gap=1)
    return branch_input, force_rebuild, repo_url_input


@app.cell
def _(mo):
    build_button = mo.ui.run_button(label="Build Simulator", kind="success")
    build_button
    return (build_button,)


@app.cell
def _(
    ICO_DNA_SM,
    ICO_LINK,
    branch_input,
    build_button,
    force_rebuild,
    get_svc,
    json,
    mo,
    repo_url_input,
    status_badge,
    time,
    traceback,
):
    # Reactive: only runs when build_button is clicked
    _sim_output = mo.Html("")
    _sim_id_val = None

    if build_button.value:
        _svc = get_svc()
        try:
            # Step 1: fetch latest
            _latest = _svc.submit_get_latest_simulator(
                repo_url=repo_url_input.value or None,
                branch=branch_input.value or None,
            )
            # Step 2: upload
            _uploaded = _svc.submit_upload_simulator(simulator=_latest, force=force_rebuild.value)
            _sim_id_val = _uploaded.database_id

            # Step 3: poll build status
            _status = "pending"
            _polls = []
            while _status not in ("completed", "failed", "cancelled"):
                time.sleep(5)
                _status = _svc.submit_get_simulator_build_status(simulator=_uploaded)
                _polls.append(_status)

            _details = json.dumps(_uploaded.model_dump(), indent=2, default=str)
            _badge = status_badge(_status)
            _dna = ICO_DNA_SM.text
            _link = ICO_LINK.text
            _sim_output = mo.Html(
                f"<div class='memphis-card'>"
                f"{_dna} <strong>Simulator ID:</strong> {_uploaded.database_id}<br>"
                f"{_dna} <strong>Status:</strong> {_badge.text}<br>"
                f"{_link} <strong>Commit:</strong> {_uploaded.git_commit_hash}<br>"
                f"<pre style='font-size:0.75rem; max-height:200px; overflow:auto;'>{_details}</pre>"
                f"</div>"
            )
        except Exception:
            _sim_output = mo.Html(
                f"<div class='memphis-card' style='border-color:var(--memphis-red);'>"
                f"<span class='memphis-status-failed'>ERROR</span><br>"
                f"<pre style='font-size:0.75rem;'>{traceback.format_exc()}</pre></div>"
            )

    _sim_output
    return


@app.cell
def _(mo):
    list_sims_button = mo.ui.run_button(label="List Simulators")
    list_sims_button
    return (list_sims_button,)


@app.cell
def _(get_svc, list_sims_button, mo):
    _sims_table = mo.Html("")
    if list_sims_button.value:
        _svc = get_svc()
        try:
            _sims = _svc.show_simulators()
            _rows = [s.model_dump() for s in _sims]
            if _rows:
                _sims_table = mo.ui.table(
                    data=_rows,
                    label="Registered Simulators",
                )
            else:
                _sims_table = mo.Html("<em>No simulators found.</em>")
        except Exception as e:
            _sims_table = mo.Html(f"<span class='memphis-status-failed'>Error: {e}</span>")
    _sims_table
    return


@app.cell
def _(mo):
    sim_status_id = mo.ui.number(label="Simulator ID", start=1, stop=99999, value=1)
    sim_status_button = mo.ui.run_button(label="Check Build Status")
    mo.hstack([sim_status_id, sim_status_button], justify="start", gap=1)
    return sim_status_button, sim_status_id


@app.cell
def _(
    get_svc,
    json,
    mo,
    sim_status_button,
    sim_status_id,
    status_badge,
    traceback,
):
    _build_status_output = mo.Html("")
    if sim_status_button.value:
        _svc = get_svc()
        try:
            _hpcrun = _svc.submit_get_simulator_build_status_full(simulator_id=int(sim_status_id.value))
            _s = _hpcrun.status.value if _hpcrun.status else "unknown"
            _badge = status_badge(_s)
            _details = json.dumps(_hpcrun.model_dump(), indent=2, default=str)
            _err = (
                f"<br><span class='memphis-status-failed'>Error: {_hpcrun.error_message}</span>"
                if _hpcrun.error_message
                else ""
            )
            _build_status_output = mo.Html(
                f"<div class='memphis-card'>"
                f"<strong>Build Status:</strong> {_badge.text}{_err}<br>"
                f"<pre style='font-size:0.75rem; max-height:200px; overflow:auto;'>{_details}</pre>"
                f"</div>"
            )
        except Exception:
            _build_status_output = mo.Html(
                f"<div class='memphis-card' style='border-color:var(--memphis-red);'>"
                f"<span class='memphis-status-failed'>ERROR</span><br>"
                f"<pre style='font-size:0.75rem;'>{traceback.format_exc()}</pre></div>"
            )
    _build_status_output
    return


@app.cell
def _(ICO_TEST_TUBE, mo):
    mo.md(f"""
    <p class="memphis-title">{ICO_TEST_TUBE.text} Simulation</p>
    """)
    return


@app.cell(hide_code=True)
def _(ICO_DNA, mo):
    mo.md(f"""
    <p class="memphis-subtitle">{ICO_DNA.text} submit \u00b7 poll \u00b7 monitor {ICO_DNA.text}</p>
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    <div class="memphis-banner"></div>
    """)
    return


@app.cell
def _(mo):
    exp_id_input = mo.ui.text(value="", label="Experiment ID", full_width=True)
    sim_id_input = mo.ui.number(label="Simulator ID", start=1, stop=99999, value=1)
    config_dropdown = mo.ui.dropdown(
        options={
            "Default": "api_simulation_default.json",
            "CCAM": "api_simulation_default_ccam.json",
            "AWS CDK": "api_simulation_default_aws_cdk.json",
            "Violacein (w/ metabolism)": "api_test_violacein_with_metabolism.json",
            "Violacein (no metabolism)": "api_test_violacein_no_metabolism.json",
            "MEC Final": "api_final_mec.json",
        },
        value="Default",
        label="Config",
    )
    gens_input = mo.ui.number(label="Generations", start=1, stop=40, step=1, value=1)
    seeds_input = mo.ui.number(label="Seeds", start=1, stop=100, step=1, value=1)
    run_parca_checkbox = mo.ui.checkbox(label="Run ParCa", value=False)
    description_input = mo.ui.text(value="", label="Description (optional)", full_width=True)

    mo.vstack([
        mo.hstack([exp_id_input], justify="start"),
        mo.hstack([sim_id_input, config_dropdown, gens_input, seeds_input, run_parca_checkbox], justify="start", gap=1),
        description_input,
    ])
    return (
        config_dropdown,
        description_input,
        exp_id_input,
        gens_input,
        run_parca_checkbox,
        seeds_input,
        sim_id_input,
    )


@app.cell
def _(mo):
    run_sim_button = mo.ui.run_button(label="Submit Simulation", kind="success")
    run_sim_button
    return (run_sim_button,)


@app.cell
def _(
    ICO_DNA_SM,
    ICO_ROCKET,
    config_dropdown,
    description_input,
    exp_id_input,
    gens_input,
    get_svc,
    json,
    mo,
    run_parca_checkbox,
    run_sim_button,
    seeds_input,
    sim_id_input,
    traceback,
):
    _run_output = mo.Html("")
    if run_sim_button.value:
        _svc = get_svc()
        _exp_id = exp_id_input.value.strip()
        if not _exp_id:
            _run_output = mo.Html("<span class='memphis-status-failed'>Experiment ID is required.</span>")
        else:
            try:
                _desc = description_input.value.strip() or (
                    f"sim{int(sim_id_input.value)}-{_exp_id}; "
                    f"{int(gens_input.value)} Generations; {int(seeds_input.value)} Seeds"
                )
                _simulation = _svc.run_workflow(
                    experiment_id=_exp_id,
                    simulator_id=int(sim_id_input.value),
                    config_filename=config_dropdown.value,
                    num_generations=int(gens_input.value),
                    num_seeds=int(seeds_input.value),
                    description=_desc,
                    run_parameter_calculator=run_parca_checkbox.value,
                )
                _details = json.dumps(_simulation.model_dump(), indent=2, default=str)
                _dna = ICO_DNA_SM.text
                _rocket = ICO_ROCKET.text
                _run_output = mo.Html(
                    f"<div class='memphis-card'>"
                    f"{_rocket} <span class='memphis-status-completed'>SUBMITTED</span><br>"
                    f"{_dna} <strong>Simulation ID:</strong> {_simulation.database_id}<br>"
                    f"{_dna} <strong>Experiment:</strong> {_simulation.experiment_id}<br>"
                    f"<pre style='font-size:0.75rem; max-height:200px; overflow:auto;'>{_details}</pre>"
                    f"</div>"
                )
            except Exception:
                _run_output = mo.Html(
                    f"<div class='memphis-card' style='border-color:var(--memphis-red);'>"
                    f"<span class='memphis-status-failed'>ERROR</span><br>"
                    f"<pre style='font-size:0.75rem;'>{traceback.format_exc()}</pre></div>"
                )
    _run_output
    return


@app.cell
def _(mo):
    poll_sim_id = mo.ui.number(label="Simulation ID", start=1, stop=99999, value=1)
    poll_sim_button = mo.ui.run_button(label="Check Status")
    poll_sim_poll = mo.ui.checkbox(label="Poll until done", value=False)
    mo.hstack([poll_sim_id, poll_sim_button, poll_sim_poll], justify="start", gap=1)
    return poll_sim_button, poll_sim_id, poll_sim_poll


@app.cell
def _(
    get_svc,
    json,
    mo,
    poll_sim_button,
    poll_sim_id,
    poll_sim_poll,
    status_badge,
    time,
    traceback,
):
    _poll_output = mo.Html("")
    if poll_sim_button.value:
        _svc = get_svc()
        _sid = int(poll_sim_id.value)
        try:
            _run = _svc.get_workflow_status(simulation_id=_sid)
            _status = _run.status.value

            if poll_sim_poll.value:
                while _status not in ("completed", "failed", "cancelled", "unknown"):
                    time.sleep(15)
                    _run = _svc.get_workflow_status(simulation_id=_sid)
                    _status = _run.status.value

            _badge = status_badge(_status)
            _err = (
                f"<br><span class='memphis-status-failed'>Error: {_run.error_message}</span>"
                if _run.error_message
                else ""
            )
            # Also fetch full simulation details
            try:
                _sim_detail = _svc.get_workflow(simulation_id=_sid)
                _detail_json = json.dumps(_sim_detail.model_dump(), indent=2, default=str)
            except Exception:
                _detail_json = "(details not available)"

            _poll_output = mo.Html(
                f"<div class='memphis-card'>"
                f"<strong>Simulation {_sid}:</strong> {_badge.text}{_err}<br>"
                f"<pre style='font-size:0.75rem; max-height:200px; overflow:auto;'>{_detail_json}</pre>"
                f"</div>"
            )
        except Exception:
            _poll_output = mo.Html(
                f"<div class='memphis-card' style='border-color:var(--memphis-red);'>"
                f"<span class='memphis-status-failed'>ERROR</span><br>"
                f"<pre style='font-size:0.75rem;'>{traceback.format_exc()}</pre></div>"
            )
    _poll_output
    return


@app.cell
def _(mo):
    list_workflows_button = mo.ui.run_button(label="List Simulations")
    list_workflows_button
    return (list_workflows_button,)


@app.cell
def _(get_svc, list_workflows_button, mo):
    _wf_table = mo.Html("")
    if list_workflows_button.value:
        _svc = get_svc()
        try:
            _workflows = _svc.show_workflows()
            _rows = [w.model_dump() for w in _workflows]
            if _rows:
                _wf_table = mo.ui.table(data=_rows, label="Simulations")
            else:
                _wf_table = mo.Html("<em>No simulations found.</em>")
        except Exception as e:
            _wf_table = mo.Html(f"<span class='memphis-status-failed'>Error: {e}</span>")
    _wf_table
    return


@app.cell
def _(mo):
    cancel_sim_id = mo.ui.number(label="Simulation ID to cancel", start=1, stop=99999, value=1)
    cancel_button = mo.ui.run_button(label="Cancel Simulation", kind="danger")
    mo.hstack([cancel_sim_id, cancel_button], justify="start", gap=1)
    return cancel_button, cancel_sim_id


@app.cell
def _(
    cancel_button,
    cancel_sim_id,
    get_svc,
    json,
    mo,
    status_badge,
    traceback,
):
    _cancel_output = mo.Html("")
    if cancel_button.value:
        _svc = get_svc()
        try:
            _result = _svc.cancel_workflow(simulation_id=int(cancel_sim_id.value))
            _badge = status_badge(_result.status.value)
            _cancel_output = mo.Html(
                f"<div class='memphis-card'>"
                f"<strong>Cancel result:</strong> {_badge.text}<br>"
                f"<pre style='font-size:0.75rem;'>{json.dumps(_result.model_dump(), indent=2, default=str)}</pre>"
                f"</div>"
            )
        except Exception:
            _cancel_output = mo.Html(
                f"<div class='memphis-card' style='border-color:var(--memphis-red);'>"
                f"<span class='memphis-status-failed'>ERROR</span><br>"
                f"<pre style='font-size:0.75rem;'>{traceback.format_exc()}</pre></div>"
            )
    _cancel_output
    return


@app.cell
def _(ICO_FILE_FOLDER, mo):
    mo.md(f"""
    <p class="memphis-title">{ICO_FILE_FOLDER.text} Outputs</p>
    """)
    return


@app.cell(hide_code=True)
def _(ICO_DNA, mo):
    mo.md(f"""
    <p class="memphis-subtitle">{ICO_DNA.text} download \u00b7 extract \u00b7 browse {ICO_DNA.text}</p>
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    <div class="memphis-banner"></div>
    """)
    return


@app.cell
def _(mo):
    dl_sim_id = mo.ui.number(label="Simulation ID", start=1, stop=99999, value=1)
    dl_dest = mo.ui.text(value="./debug", label="Destination directory", full_width=True)
    dl_button = mo.ui.run_button(label="Download Outputs", kind="success")
    mo.hstack([dl_sim_id, dl_dest, dl_button], justify="start", gap=1)
    return dl_button, dl_dest, dl_sim_id


@app.cell
def _(
    ICO_DNA_SM,
    ICO_DOWN_ARROW,
    Path,
    dl_button,
    dl_dest,
    dl_sim_id,
    get_svc,
    mo,
    traceback,
):
    import asyncio as _asyncio

    _dl_output = mo.Html("")
    if dl_button.value:
        _svc = get_svc()
        _sid = int(dl_sim_id.value)
        _dest = Path(dl_dest.value.strip() or f"simulation_id_{_sid}")
        try:
            _extracted = _asyncio.run(_svc.get_output_data(simulation_id=_sid, dest=_dest))
            # List downloaded files
            _files = sorted(str(f.relative_to(_extracted)) for f in _extracted.rglob("*") if f.is_file())
            _file_count = len(_files)
            _file_list = "\n".join(_files[:50])
            _truncated = f"\n... and {_file_count - 50} more" if _file_count > 50 else ""
            _dna = ICO_DNA_SM.text
            _arrow = ICO_DOWN_ARROW.text
            _dl_output = mo.Html(
                f"<div class='memphis-card'>"
                f"{_arrow} <span class='memphis-status-completed'>DOWNLOAD COMPLETE</span><br>"
                f"{_dna} <strong>Extracted to:</strong> {_extracted}<br>"
                f"{_dna} <strong>Files:</strong> {_file_count}<br>"
                f"<pre style='font-size:0.7rem; max-height:300px; overflow:auto;'>{_file_list}{_truncated}</pre>"
                f"</div>"
            )
        except Exception:
            _dl_output = mo.Html(
                f"<div class='memphis-card' style='border-color:var(--memphis-red);'>"
                f"<span class='memphis-status-failed'>ERROR</span><br>"
                f"<pre style='font-size:0.75rem;'>{traceback.format_exc()}</pre></div>"
            )
    _dl_output
    return


@app.cell
def _(CYAN, ICO_DNA_SM, ICO_MICROBE, MAGENTA, mo):
    _dna = ICO_DNA_SM.text
    _microbe = ICO_MICROBE.text
    mo.Html(
        '<div class="memphis-banner" style="margin-top:2rem;"></div>'
        f'<p style="text-align:center; font-size:0.7rem; font-family: monospace; '
        f'color: {CYAN};">'
        f"{_dna} simulating {_dna} microbial {_dna} systems {_dna}"
        f"</p>"
        f'<p style="text-align:center; font-size:0.6rem; color: {MAGENTA};">'
        f"{_microbe} simulating microbial systems \u2014 whole-cell E. coli platform \u2014 UCONN CCAM {_microbe}</p>"
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
