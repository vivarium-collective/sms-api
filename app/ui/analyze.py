import marimo

__generated_with = "0.14.17"
app = marimo.App(width="full", layout_file="layouts/analyze.grid.json")


@app.cell
def _():
    from pathlib import Path
    import os
    import marimo as mo

    def get_html_output_paths(outdir_root: Path, experiment_id: str):
        outdir = outdir_root / experiment_id
        filepaths = []
        for root, _, files in outdir.walk():
            for f in files:
                fp = root / f
                if fp.exists() and fp.is_file():
                    filepaths.append(fp)
        return list(filter(lambda _file: _file.name.endswith(".html"), filepaths))

    def read_html_file(file_path: str) -> str:
        """Read an HTML file and return its contents as a single string."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def analysis_ui(outdir_root: Path):
        filepaths = get_html_output_paths(outdir_root, "analysis_multigen")
        iframes = [mo.iframe(read_html_file(path)) for path in filepaths]
        ui = mo.vstack(iframes)
        return ui

    return Path, analysis_ui, mo, os


@app.cell
def _(mo):
    get_ui, set_ui = mo.state(None)
    return get_ui, set_ui


@app.cell
def _(Path, analysis_ui, os):
    from sms_api.config import get_settings

    env = get_settings()
    # outdir_root = Path(env.slurm_base_path) / "workspace" / "api_outputs"
    outdir_root = Path(os.getenv("HOME")) / "sms" / "vEcoli" / "api_outputs"
    ui = analysis_ui(outdir_root)
    return (ui,)


@app.cell
def _(mo):
    btn = mo.ui.run_button(label="Run Multigeneration Analysis", kind="success")
    btn
    return (btn,)


@app.cell
def _(btn, get_ui, set_ui, ui):
    interface = get_ui()
    if btn.value:
        set_ui(ui)
        interface = get_ui()

    interface
    return


app._unparsable_cell(
    r"""
    http://localhost:8888/analyses/{id}

    import httpx

    with httpx.Client() as client:
        resp =
    """,
    name="_",
)


app._unparsable_cell(
    r"""
    http://localhost:8888/experiments/launch
    """,
    name="_",
)


if __name__ == "__main__":
    app.run()
