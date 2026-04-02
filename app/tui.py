"""Atlantis TUI — Rich-based interactive terminal interface for SMS API.

Launch via:
    atlantis tui [--base-url URL]

Or directly:
    uv run python -m app.tui
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from app.app_data_service import BaseUrl, E2EDataService, get_data_service

# ─── Theme ────────────────────────────────────────────────────────────────────

ACCENT = "bright_cyan"
ACCENT2 = "bright_magenta"
SUCCESS = "bright_green"
WARN = "bright_yellow"
ERR = "bright_red"
DIM = "dim"
HEADER_STYLE = Style(color="bright_cyan", bold=True)
MENU_NUM_STYLE = Style(color="bright_magenta", bold=True)
MENU_LABEL_STYLE = Style(color="white")

BANNER = r"""[bright_cyan]
     █████╗ ████████╗██╗      █████╗ ███╗   ██╗████████╗██╗███████╗
    ██╔══██╗╚══██╔══╝██║     ██╔══██╗████╗  ██║╚══██╔══╝██║██╔════╝
    ███████║   ██║   ██║     ███████║██╔██╗ ██║   ██║   ██║███████╗
    ██╔══██║   ██║   ██║     ██╔══██║██║╚██╗██║   ██║   ██║╚════██║
    ██║  ██║   ██║   ███████╗██║  ██║██║ ╚████║   ██║   ██║███████║
    ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚══════╝[/]
"""

SUB_BANNER = "[dim]Simulating Microbial Systems — Interactive Terminal[/dim]"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _json_panel(data: Any, title: str = "") -> Panel:
    import json

    formatted = json.dumps(data, indent=2, default=str)
    syntax = Syntax(formatted, "json", theme="monokai", line_numbers=False, word_wrap=True)
    return Panel(syntax, title=title, border_style=ACCENT, expand=False)


def _status_color(status: str) -> str:
    s = status.lower()
    if s in ("completed", "complete"):
        return SUCCESS
    if s in ("running", "active"):
        return ACCENT
    if s in ("failed", "error"):
        return ERR
    if s in ("cancelled", "canceled"):
        return WARN
    if s in ("pending", "queued", "waiting"):
        return ACCENT2
    return "white"


def _make_menu(title: str, items: list[tuple[str, str]]) -> Panel:
    """Build a numbered menu panel."""
    table = Table(show_header=False, box=None, padding=(0, 2), expand=False)
    table.add_column(style=MENU_NUM_STYLE, width=4, justify="right")
    table.add_column(style=MENU_LABEL_STYLE)
    for idx, (label, desc) in enumerate(items, 1):
        table.add_row(f"[{ACCENT2}]{idx}[/]", f"[bold]{label}[/bold]  [dim]{desc}[/dim]")
    table.add_row(f"[{ERR}]0[/]", f"[{ERR}]Back / Quit[/{ERR}]")
    return Panel(table, title=f"[bold]{title}[/bold]", border_style=ACCENT, expand=False)


def _pick(console: Console, prompt_text: str, max_val: int) -> int:
    while True:
        raw = Prompt.ask(f"[{ACCENT2}]{prompt_text}[/]", console=console, default="0")
        try:
            val = int(raw)
            if 0 <= val <= max_val:
                return val
        except ValueError:
            pass
        console.print(f"[{ERR}]Enter a number between 0 and {max_val}.[/{ERR}]")


# ─── TUI Class ────────────────────────────────────────────────────────────────


class AtlantisTUI:
    def __init__(self, base_url: BaseUrl | str = BaseUrl.STANFORD_DEV_FORWARDED) -> None:
        self.console = Console()
        self.base_url = BaseUrl(base_url)
        self.svc: E2EDataService = get_data_service(base_url=self.base_url)

    # ── Entrypoint ───────────────────────────────────────────────────────

    def run(self) -> None:
        self.console.clear()
        self.console.print(Align.center(BANNER))
        self.console.print(Align.center(Text.from_markup(SUB_BANNER)))
        self.console.print(Align.center(Text.from_markup(f"[dim]Server:[/dim] [{ACCENT}]{self.base_url}[/{ACCENT}]")))
        self.console.print()

        while True:
            menu = _make_menu(
                "Main Menu",
                [
                    ("Simulations", "Run, inspect, cancel, download outputs"),
                    ("Simulators", "List versions, check build status"),
                    ("Parca", "Parameter calculator datasets & status"),
                    ("Analyses", "Inspect analysis jobs, logs, plots"),
                    ("Demo: Download Data", "Download simulation outputs to local disk"),
                    ("Change Server", "Switch the API base URL"),
                ],
            )
            self.console.print(menu)
            choice = _pick(self.console, "Select", 6)

            if choice == 0:
                self.console.print(f"\n[{ACCENT}]Goodbye![/{ACCENT}]\n")
                return
            if choice == 1:
                self._simulations_menu()
            elif choice == 2:
                self._simulators_menu()
            elif choice == 3:
                self._parca_menu()
            elif choice == 4:
                self._analyses_menu()
            elif choice == 5:
                self._demo_download()
            elif choice == 6:
                self._change_server()

    # ── Server ───────────────────────────────────────────────────────────

    def _change_server(self) -> None:
        urls = list(BaseUrl)
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style=MENU_NUM_STYLE, width=4, justify="right")
        table.add_column()
        for i, u in enumerate(urls, 1):
            marker = " [green]*[/green]" if u == self.base_url else ""
            table.add_row(str(i), f"{u.name}  [dim]{u.value}[/dim]{marker}")
        self.console.print(Panel(table, title="Select Server", border_style=ACCENT))
        idx = _pick(self.console, "Server #", len(urls))
        if idx == 0:
            return
        self.base_url = urls[idx - 1]
        self.svc = get_data_service(base_url=self.base_url)
        self.console.print(f"[{SUCCESS}]Switched to {self.base_url.name} ({self.base_url.value})[/{SUCCESS}]\n")

    # ── Simulations ──────────────────────────────────────────────────────

    def _simulations_menu(self) -> None:
        while True:
            menu = _make_menu(
                "Simulations",
                [
                    ("List", "Show all simulations"),
                    ("Get", "Fetch simulation by ID"),
                    ("Status", "Check simulation status + log"),
                    ("Run", "Submit a new simulation workflow"),
                    ("Cancel", "Cancel a running simulation"),
                    ("Download Outputs", "Download output archive"),
                ],
            )
            self.console.print(menu)
            choice = _pick(self.console, "Simulations", 6)
            if choice == 0:
                return
            try:
                if choice == 1:
                    self._sim_list()
                elif choice == 2:
                    self._sim_get()
                elif choice == 3:
                    self._sim_status()
                elif choice == 4:
                    self._sim_run()
                elif choice == 5:
                    self._sim_cancel()
                elif choice == 6:
                    self._sim_outputs()
            except Exception as e:
                self.console.print(f"[{ERR}]Error: {e}[/{ERR}]\n")

    def _sim_list(self) -> None:
        with self.console.status("[bold cyan]Fetching simulations...", spinner="dots"):
            sims = self.svc.show_workflows()
        if not sims:
            self.console.print(f"[{WARN}]No simulations found.[/{WARN}]\n")
            return
        table = Table(title="Simulations", border_style=ACCENT, show_lines=True)
        table.add_column("ID", style="bold", justify="right")
        table.add_column("Experiment", style=ACCENT2)
        table.add_column("Simulator", justify="right")
        table.add_column("Config", style=DIM)
        table.add_column("Generations", justify="center")
        table.add_column("Job ID", style=DIM)
        for s in sims:
            table.add_row(
                str(s.database_id),
                s.experiment_id,
                str(s.simulator_id),
                s.simulation_config_filename,
                str(s.config.generations),
                s.job_id or "-",
            )
        self.console.print(table)
        self.console.print()

    def _sim_get(self) -> None:
        sid = IntPrompt.ask(f"[{ACCENT2}]Simulation ID[/]", console=self.console)
        with self.console.status("[bold cyan]Fetching...", spinner="dots"):
            sim = self.svc.get_workflow(simulation_id=sid)
        self.console.print(_json_panel(sim.model_dump(), title=f"Simulation {sid}"))
        self.console.print()

    def _sim_status(self) -> None:
        sid = IntPrompt.ask(f"[{ACCENT2}]Simulation ID[/]", console=self.console)
        with self.console.status("[bold cyan]Checking status...", spinner="dots"):
            status = self.svc.get_workflow_status(simulation_id=sid)
        color = _status_color(status)
        self.console.print(f"  Status: [{color}][bold]{status.upper()}[/bold][/{color}]")
        if Confirm.ask(f"[{DIM}]Show full log?[/]", default=False, console=self.console):
            with self.console.status("[bold cyan]Fetching log...", spinner="dots"):
                log = self.svc.get_workflow_log(simulation_id=sid)
            self.console.print(Panel(log, title=f"Log (sim {sid})", border_style="cyan"))
        self.console.print()

    def _sim_run(self) -> None:
        from sms_api.common.simulator_defaults import SimulationConfigFilename as SCF

        experiment_id = Prompt.ask(f"[{ACCENT2}]Experiment ID[/]", console=self.console)
        simulator_id = IntPrompt.ask(f"[{ACCENT2}]Simulator ID[/]", console=self.console)

        configs = list(SCF)
        for i, c in enumerate(configs, 1):
            self.console.print(f"  [{ACCENT2}]{i}[/] {c.name}  [dim]{c.value}[/dim]")
        cidx = _pick(self.console, "Config #", len(configs))
        if cidx == 0:
            return
        config = configs[cidx - 1]

        gens = IntPrompt.ask(f"[{ACCENT2}]Generations[/]", default=1, console=self.console)
        seeds = IntPrompt.ask(f"[{ACCENT2}]Seeds[/]", default=3, console=self.console)
        desc = Prompt.ask(f"[{ACCENT2}]Description[/]", default="", console=self.console) or None
        run_parca = Confirm.ask(f"[{ACCENT2}]Run parca?[/]", default=False, console=self.console)

        with self.console.status("[bold cyan]Submitting...", spinner="dots"):
            sim = self.svc.run_workflow(
                experiment_id=experiment_id,
                simulator_id=simulator_id,
                config_filename=config.value,
                num_generations=gens,
                num_seeds=seeds,
                description=desc,
                run_parameter_calculator=run_parca,
            )
        self.console.print(f"[{SUCCESS}]Simulation submitted![/{SUCCESS}]")
        self.console.print(_json_panel(sim.model_dump(), title="New Simulation"))
        self.console.print()

    def _sim_cancel(self) -> None:
        sid = IntPrompt.ask(f"[{ACCENT2}]Simulation ID to cancel[/]", console=self.console)
        if not Confirm.ask(f"[{WARN}]Cancel simulation {sid}?[/]", default=False, console=self.console):
            return
        with self.console.status("[bold cyan]Cancelling...", spinner="dots"):
            result = self.svc.cancel_workflow(simulation_id=sid)
        color = _status_color(result.status.value)
        self.console.print(f"  [{color}]Simulation {sid}: {result.status.value.upper()}[/{color}]\n")

    def _sim_outputs(self) -> None:
        sid = IntPrompt.ask(f"[{ACCENT2}]Simulation ID[/]", console=self.console)
        dest = Prompt.ask(
            f"[{ACCENT2}]Destination directory[/]", default=f"./simulation_id_{sid}", console=self.console
        )
        dest_path = Path(dest).resolve()
        dest_path.mkdir(parents=True, exist_ok=True)
        self.console.print(f"[{ACCENT}]Downloading to {dest_path}...[/{ACCENT}]")
        result = asyncio.run(self.svc.get_output_data(simulation_id=sid, dest=dest_path))
        self.console.print(f"[{SUCCESS}]Saved to: {result}[/{SUCCESS}]\n")

    # ── Simulators ───────────────────────────────────────────────────────

    def _simulators_menu(self) -> None:
        while True:
            menu = _make_menu(
                "Simulators",
                [
                    ("List", "Show all registered simulator versions"),
                    ("Status", "Check build status by ID"),
                    ("Build Latest", "Fetch + upload + build latest vEcoli"),
                ],
            )
            self.console.print(menu)
            choice = _pick(self.console, "Simulators", 3)
            if choice == 0:
                return
            try:
                if choice == 1:
                    self._sim_version_list()
                elif choice == 2:
                    self._sim_version_status()
                elif choice == 3:
                    self._sim_version_latest()
            except Exception as e:
                self.console.print(f"[{ERR}]Error: {e}[/{ERR}]\n")

    def _sim_version_list(self) -> None:
        with self.console.status("[bold cyan]Fetching simulators...", spinner="dots"):
            simulators = self.svc.show_simulators()
        if not simulators:
            self.console.print(f"[{WARN}]No simulators found.[/{WARN}]\n")
            return
        table = Table(title="Registered Simulators", border_style=ACCENT, show_lines=True)
        table.add_column("DB ID", style="bold", justify="right")
        table.add_column("Commit", style=ACCENT2)
        table.add_column("Branch")
        table.add_column("Repo", style=DIM, max_width=50)
        table.add_column("Created", style=DIM)
        for sv in simulators:
            table.add_row(
                str(sv.database_id),
                sv.git_commit_hash[:12],
                sv.git_branch,
                sv.git_repo_url.rsplit("/", 1)[-1] if "/" in sv.git_repo_url else sv.git_repo_url,
                str(sv.created_at)[:19] if sv.created_at else "-",
            )
        self.console.print(table)
        self.console.print()

    def _sim_version_status(self) -> None:
        sid = IntPrompt.ask(f"[{ACCENT2}]Simulator ID[/]", console=self.console)
        with self.console.status("[bold cyan]Checking build status...", spinner="dots"):
            status = self.svc.get_simulator_status(simulator_id=sid)
        color = _status_color(status)
        self.console.print(f"  Build status: [{color}][bold]{status.upper()}[/bold][/{color}]\n")

    def _sim_version_latest(self) -> None:
        self.console.print(f"[{ACCENT}]Fetching, uploading, and building latest simulator...[/{ACCENT}]")
        self.console.print(f"[{DIM}](This may take a while — polling build status)[/{DIM}]")
        with self.console.status("[bold cyan]Building...", spinner="dots"):
            sv = self.svc.get_simulator()
        self.console.print(f"[{SUCCESS}]Simulator ready![/{SUCCESS}]")
        self.console.print(_json_panel(sv.model_dump(), title="Built Simulator"))
        self.console.print()

    # ── Parca ────────────────────────────────────────────────────────────

    def _parca_menu(self) -> None:
        while True:
            menu = _make_menu(
                "Parca",
                [
                    ("List Datasets", "Show all parca datasets"),
                    ("Status", "Check parca run status by ID"),
                ],
            )
            self.console.print(menu)
            choice = _pick(self.console, "Parca", 2)
            if choice == 0:
                return
            try:
                if choice == 1:
                    self._parca_list()
                elif choice == 2:
                    self._parca_status()
            except Exception as e:
                self.console.print(f"[{ERR}]Error: {e}[/{ERR}]\n")

    def _parca_list(self) -> None:
        with self.console.status("[bold cyan]Fetching parca datasets...", spinner="dots"):
            datasets = self.svc.get_parca_datasets()
        if not datasets:
            self.console.print(f"[{WARN}]No parca datasets found.[/{WARN}]\n")
            return
        table = Table(title="Parca Datasets", border_style=ACCENT, show_lines=True)
        table.add_column("DB ID", style="bold", justify="right")
        table.add_column("Simulator ID", justify="right")
        table.add_column("Archive Path", style=DIM, max_width=60)
        for ds in datasets:
            table.add_row(
                str(ds.database_id),
                str(ds.parca_dataset_request.simulator_version.database_id),
                ds.remote_archive_path or "-",
            )
        self.console.print(table)
        self.console.print()

    def _parca_status(self) -> None:
        pid = IntPrompt.ask(f"[{ACCENT2}]Parca ID[/]", console=self.console)
        with self.console.status("[bold cyan]Checking parca status...", spinner="dots"):
            hpc_run = self.svc.get_parca_status(parca_id=pid)
        self.console.print(_json_panel(hpc_run.model_dump(), title=f"Parca Run {pid}"))
        self.console.print()

    # ── Analyses ─────────────────────────────────────────────────────────

    def _analyses_menu(self) -> None:
        while True:
            menu = _make_menu(
                "Analyses",
                [
                    ("Get", "Fetch analysis spec by ID"),
                    ("Status", "Check analysis run status"),
                    ("Log", "View analysis run log"),
                    ("Plots", "Get analysis plot outputs"),
                ],
            )
            self.console.print(menu)
            choice = _pick(self.console, "Analyses", 4)
            if choice == 0:
                return
            try:
                if choice == 1:
                    self._analysis_get()
                elif choice == 2:
                    self._analysis_status()
                elif choice == 3:
                    self._analysis_log()
                elif choice == 4:
                    self._analysis_plots()
            except Exception as e:
                self.console.print(f"[{ERR}]Error: {e}[/{ERR}]\n")

    def _analysis_get(self) -> None:
        aid = IntPrompt.ask(f"[{ACCENT2}]Analysis ID[/]", console=self.console)
        with self.console.status("[bold cyan]Fetching analysis...", spinner="dots"):
            analysis = self.svc.get_analysis(analysis_id=aid)
        self.console.print(_json_panel(analysis.model_dump(), title=f"Analysis {aid}"))
        self.console.print()

    def _analysis_status(self) -> None:
        aid = IntPrompt.ask(f"[{ACCENT2}]Analysis ID[/]", console=self.console)
        with self.console.status("[bold cyan]Checking status...", spinner="dots"):
            status = self.svc.get_analysis_status(analysis_id=aid)
        color = _status_color(status.status.value)
        self.console.print(f"  Analysis {aid}: [{color}][bold]{status.status.value.upper()}[/bold][/{color}]")
        if status.error_log:
            self.console.print(Panel(status.error_log, title="Error Log", border_style=ERR))
        self.console.print()

    def _analysis_log(self) -> None:
        aid = IntPrompt.ask(f"[{ACCENT2}]Analysis ID[/]", console=self.console)
        with self.console.status("[bold cyan]Fetching log...", spinner="dots"):
            log = self.svc.get_analysis_log(analysis_id=aid)
        self.console.print(Panel(log, title=f"Analysis Log ({aid})", border_style="cyan"))
        self.console.print()

    def _analysis_plots(self) -> None:
        aid = IntPrompt.ask(f"[{ACCENT2}]Analysis ID[/]", console=self.console)
        with self.console.status("[bold cyan]Fetching plots...", spinner="dots"):
            plots = self.svc.get_analysis_plots(analysis_id=aid)
        if not plots:
            self.console.print(f"[{WARN}]No plots found.[/{WARN}]\n")
            return
        tree = Tree(f"[bold]Analysis {aid} Plots[/bold]")
        for p in plots:
            node = tree.add(f"[{ACCENT2}]{p.name}[/{ACCENT2}]")
            preview = p.content[:120].replace("\n", " ") + "..." if len(p.content) > 120 else p.content
            node.add(f"[{DIM}]{preview}[/{DIM}]")
        self.console.print(tree)
        self.console.print()

    # ── Demo Download ────────────────────────────────────────────────────

    def _demo_download(self) -> None:
        """Download S3 simulation outputs directly — same flow as test_outputs.py."""
        import os
        import tarfile
        from urllib.parse import urlparse

        test_outdir = os.environ.get("TEST_BUCKET_EXPERIMENT_OUTDIR", "")
        if not test_outdir:
            self.console.print(
                f"[{ERR}]TEST_BUCKET_EXPERIMENT_OUTDIR is not set.[/{ERR}]\n"
                f"[{DIM}]Set it in assets/dev/config/.dev_env or your environment.[/{DIM}]"
            )
            return

        experiment_id = urlparse(test_outdir).path.strip("/").rsplit("/", 1)[-1]
        self.console.print(f"[{ACCENT}]Experiment ID:[/{ACCENT}] [bold]{experiment_id}[/bold]")
        self.console.print(f"[{DIM}]Source: {test_outdir}[/{DIM}]\n")

        dest = Prompt.ask(f"[{ACCENT2}]Destination[/]", default="./demo_outputs", console=self.console)
        dest_path = Path(dest).resolve()
        local_cache = dest_path / experiment_id
        local_cache.mkdir(parents=True, exist_ok=True)

        from sms_api.common.storage.file_service_s3 import FileServiceS3
        from sms_api.config import get_settings
        from sms_api.dependencies import get_file_service, set_file_service

        settings = get_settings()
        if not settings.storage_s3_bucket or not settings.storage_s3_region:
            self.console.print(f"[{ERR}]S3 settings not configured (STORAGE_S3_BUCKET, STORAGE_S3_REGION).[/{ERR}]")
            return

        self.console.print(
            f"  [{DIM}]Bucket: {settings.storage_s3_bucket}  Region: {settings.storage_s3_region}[/{DIM}]"
        )

        saved_fs = get_file_service()
        fs = FileServiceS3()
        set_file_service(fs)

        try:
            from sms_api.common.handlers.simulations import _download_outputs_from_s3

            with self.console.status("[bold cyan]Downloading from S3...", spinner="dots"):
                asyncio.run(_download_outputs_from_s3(experiment_id, local_cache))

            real_files = [f for f in local_cache.rglob("*") if f.is_file()]
            if not real_files:
                self.console.print(f"[{ERR}]No files downloaded.[/{ERR}]")
                return

            tsv_count = sum(1 for f in real_files if f.suffix == ".tsv")
            json_count = sum(1 for f in real_files if f.suffix == ".json")

            archive_path = dest_path / f"{experiment_id}.tar.gz"
            with self.console.status("[bold cyan]Creating archive...", spinner="dots"):
                with tarfile.open(archive_path, "w:gz") as tar:
                    tar.add(str(local_cache), arcname=experiment_id)

            tree = Tree(f"[bold]{experiment_id}/[/bold]")
            tree.add(f"[{SUCCESS}]{tsv_count}[/{SUCCESS}] .tsv files")
            tree.add(f"[{ACCENT}]{json_count}[/{ACCENT}] .json files")
            tree.add(f"[{DIM}]{len(real_files)} total files[/{DIM}]")
            self.console.print(Panel(tree, title="Download Complete", border_style=SUCCESS))
            self.console.print(f"  [{SUCCESS}]Files:[/{SUCCESS}]   {local_cache}")
            self.console.print(f"  [{SUCCESS}]Archive:[/{SUCCESS}] {archive_path}\n")

        except Exception as e:
            self.console.print(f"[{ERR}]Error: {e}[/{ERR}]\n")
        finally:
            asyncio.run(fs.close())
            set_file_service(saved_fs)


# ── Direct invocation ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else BaseUrl.STANFORD_DEV_FORWARDED
    tui = AtlantisTUI(base_url=base)
    tui.run()
