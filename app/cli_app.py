from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sms_api.common import StrEnumBase

if TYPE_CHECKING:
    from rich.console import Console

    from app.app_data_service import E2EDataService
    from sms_api.common.storage.file_service_s3 import FileServiceS3

import typer
from typer import Argument, Option

from app.app_data_service import get_data_service
from app.tui import AtlantisTUI


class CliType(StrEnumBase):
    SIMULATOR = "simulator"
    SIMULATION = "simulation"
    PARCA = "parca"
    ANALYSIS = "analysis"
    DEMO = "demo"
    HELP = "help"
    TUI = "tui"


class ApiBaseUrl(StrEnumBase):
    RKE_PROD = "https://sms.cam.uchc.edu"
    RKE_DEV = "https://sms-dev.cam.uchc.edu"
    LOCAL_8888 = "http://localhost:8888"
    LOCAL_8000 = "http://localhost:8000"
    LOCAL_1111 = "http://localhost:1111"
    LOCAL_62505 = "http://localhost:62505"
    LOCAL_8080 = "http://localhost:8080"


API_BASE_URL = os.getenv("API_BASE_URL", ApiBaseUrl.LOCAL_8080)


cli = typer.Typer(name="atlantis", help="SMS API CLI for managing vEcoli simulations, simulators, parca, and analyses.")
simulator_cli = typer.Typer(help="Manage simulator (vEcoli) versions and builds.")
simulation_cli = typer.Typer(help="Run and inspect simulation workflows.")
parca_cli = typer.Typer(help="Inspect parca (parameter calculator) datasets and runs.")
analysis_cli = typer.Typer(help="Inspect analysis jobs and outputs.")
demo_cli = typer.Typer(help="Demo and utility commands.")
tui_cli = typer.Typer(help="TUI command line interface.")

cli.add_typer(simulator_cli, name="simulator")
cli.add_typer(simulation_cli, name="simulation")
cli.add_typer(parca_cli, name="parca")
cli.add_typer(analysis_cli, name="analysis")
cli.add_typer(demo_cli, name="demo")
cli.add_typer(tui_cli)


def main() -> None:
    cli()


# -- Info/Help --


@cli.command(name="help")
def display_help(app: CliType | None = typer.Argument(default=None)) -> None:
    """Show help for a specific subcommand, or the main CLI."""
    import click

    cmd = typer.main.get_command(cli)
    with click.Context(cmd) as ctx:
        if app is None:
            print(cmd.get_help(ctx))
        else:
            sub = cmd.get_command(ctx, app.value)  # type: ignore[attr-defined]
            if sub is None:
                print(f"Unknown command: {app.value}")
                raise typer.Exit(1)
            with click.Context(sub, parent=ctx) as sub_ctx:
                print(sub.get_help(sub_ctx))


# -- Top-level TUI command --


@tui_cli.command(name="tui", help="Launch the interactive terminal UI.")
def launch_tui(
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    tui = AtlantisTUI(base_url=base_url)
    tui.run()


# -- Simulator commands --


@simulator_cli.command("latest", help="Fetch, upload, and build the latest simulator version from the default repo.")
def simulator_latest(
    repo_url: str | None = Option(default=None, help="Git repo URL. Defaults to the configured default repo."),
    branch: str | None = Option(default=None, help="Git branch. Defaults to the configured default branch."),
    force: bool = Option(default=False, help="Force rebuild even if a completed build exists."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    import time

    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    data_service = get_data_service(base_url=base_url)

    # 1. Get latest commit
    with console.status("[bold cyan]Fetching latest commit..."):
        latest = data_service.submit_get_latest_simulator(repo_url=repo_url, branch=branch)
    console.print(
        f"[bold]Commit:[/bold] {latest.git_commit_hash}  [dim]({latest.git_repo_url} @ {latest.git_branch})[/dim]"
    )

    # 2. Upload (triggers build if new, or force rebuild)
    with console.status("[bold cyan]Uploading simulator..."):
        uploaded = data_service.submit_upload_simulator(simulator=latest, force=force)
    console.print(f"[bold]Simulator ID:[/bold] {uploaded.database_id}")

    # 3. Poll build status with live feedback
    console.print("[bold cyan]Waiting for build...[/bold cyan]")
    poll_interval = 15
    elapsed = 0
    status = "running"
    while status not in ("completed", "failed", "cancelled"):
        time.sleep(poll_interval)
        elapsed += poll_interval
        status = data_service.submit_get_simulator_build_status(simulator=uploaded)
        console.print(f"  [{elapsed}s] status: [yellow]{status}[/yellow]")

    style = "green" if status == "completed" else "red"
    console.print(
        Panel(
            f"[bold {style}]{status.upper()}[/bold {style}]",
            title=f"Build — simulator {uploaded.database_id}",
            border_style=style,
        )
    )
    _display(uploaded.model_dump())


@simulator_cli.command("list", help="List all registered simulator versions.")
def simulator_list(
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    simulators = data_service.show_simulators()
    for sim in simulators:
        _display(sim.model_dump())


@simulator_cli.command("status", help="Get the container build status for a simulator by its database ID.")
def simulator_status(
    simulator_id: int = Argument(help="Simulator database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    data_service = get_data_service(base_url=base_url)
    hpcrun = data_service.submit_get_simulator_build_status_full(simulator_id=simulator_id)
    style = "green" if hpcrun.status == "completed" else ("red" if hpcrun.status == "failed" else "yellow")
    console.print(
        Panel(
            f"[bold {style}]{hpcrun.status.upper() if hpcrun.status else 'no status'}[/bold {style}]",
            title=f"Build — simulator {simulator_id}",
            border_style=style,
        )
    )
    if hpcrun.error_message:
        console.print(f"[red]Error:[/red] {hpcrun.error_message}")
    _display(hpcrun.model_dump())


# -- Simulation commands --


@simulation_cli.command("run", help="Submit a simulation workflow (parca -> simulation -> analysis).")
def simulation_run(
    experiment_id: str = Argument(help="Unique experiment identifier."),
    simulator_id: int = Argument(help="Database ID of the simulator to use."),
    config_filename: str = Option(
        default="api_simulation_default.json",
        help="Config filename in vEcoli/configs/ on HPC. The server validates accepted values.",
    ),
    generations: int = Option(default=1, help="Number of generations to run per lineage (seed)."),
    seeds: int = Option(default=3, help="Number of lineages (seeds)."),
    description: str | None = Option(default=None, help="Custom description for this simulation run."),
    run_parca: bool = Option(
        default=False,
        help="Run the parameter calculator before simulation. Increases overall runtime.",
    ),
    poll: bool = Option(default=False, help="Poll simulation status until completion."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    import time

    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    data_service = get_data_service(base_url=base_url)

    with console.status("[bold cyan]Submitting simulation..."):
        simulation = data_service.run_workflow(
            experiment_id=experiment_id,
            simulator_id=simulator_id,
            config_filename=config_filename,
            num_generations=generations,
            num_seeds=seeds,
            description=description or f"sim{simulator_id}-{experiment_id}; {generations} Generations; {seeds} Seeds",
            run_parameter_calculator=run_parca,
        )

    console.print(f"[bold green]Simulation submitted![/bold green]  ID: {simulation.database_id}")
    _display(simulation.model_dump())

    if not poll:
        sim_id = simulation.database_id
        console.print(f"\n[dim]Track progress:[/dim]  atlantis simulation status {sim_id}")
        console.print(f"[dim]Download data:[/dim]   atlantis simulation outputs {sim_id} --dest ./debug")
        return

    # Poll until done
    console.print("\n[bold cyan]Polling simulation status...[/bold cyan]")
    poll_interval = 30
    elapsed = 0
    status = "running"
    run = None
    while status not in ("completed", "failed", "cancelled", "unknown"):
        time.sleep(poll_interval)
        elapsed += poll_interval
        try:
            run = data_service.get_workflow_status(simulation_id=simulation.database_id)
            status = run.status.value
        except Exception as e:
            console.print(f"  [{elapsed}s] [red]error: {e}[/red]")
            continue
        console.print(f"  [{elapsed}s] status: [yellow]{status}[/yellow]")

    style = "green" if status == "completed" else "red"
    error_detail = f"\n{run.error_message}" if run and run.error_message else ""
    console.print(
        Panel(
            f"[bold {style}]{status.upper()}[/bold {style}]{error_detail}",
            title=f"Simulation {simulation.database_id}",
            border_style=style,
        )
    )
    if status == "completed":
        console.print(
            f"\n[dim]Download data:[/dim]  atlantis simulation outputs {simulation.database_id} --dest ./debug"
        )


@simulation_cli.command("get", help="Get a simulation by its database ID.")
def simulation_get(
    simulation_id: int = Argument(help="Simulation database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    simulation = data_service.get_workflow(simulation_id=simulation_id)
    _display(simulation.model_dump())


@simulation_cli.command("list", help="List all simulations.")
def simulation_list(
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    simulations = data_service.show_workflows()
    for sim in simulations:
        _display(sim.model_dump())


def _show_simulation_result(
    console: Console,
    data_service: E2EDataService,
    simulation_id: int,
    status: str,
    error_message: str | None,
) -> None:
    """Display a terminal simulation status with details."""
    from rich.panel import Panel

    style = "green" if status == "completed" else "red"
    error_detail = f"\n{error_message}" if error_message else ""
    console.print(
        Panel(
            f"[bold {style}]{status.upper()}[/bold {style}]{error_detail}",
            title=f"Simulation {simulation_id}",
            border_style=style,
        )
    )
    try:
        sim = data_service.get_workflow(simulation_id=simulation_id)
        _display(sim.model_dump())
    except Exception as e:
        console.print(f"[dim]Details not available: {e}[/dim]")
    if status == "completed":
        console.print(f"\n[dim]Download data:[/dim]  atlantis simulation outputs {simulation_id} --dest ./debug")


@simulation_cli.command("status", help="Get the status and log for a simulation.")
def simulation_status(
    simulation_id: int = Argument(help="Simulation database ID."),
    poll: bool = Option(default=False, help="Poll until simulation completes."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    import time

    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    data_service = get_data_service(base_url=base_url)

    # Get status first (always available)
    try:
        run = data_service.get_workflow_status(simulation_id=simulation_id)
        status = run.status.value
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        return

    # Terminal state: show result panel + simulation details
    if status in ("completed", "failed", "cancelled"):
        _show_simulation_result(console, data_service, simulation_id, status, run.error_message)
        return

    # Still running: show live log
    console.print(f"[bold]Status:[/bold] [yellow]{status.upper()}[/yellow]")
    try:
        log = data_service.get_workflow_log(simulation_id=simulation_id)
        console.print(Panel(log, title=f"Workflow Log (sim {simulation_id})", border_style="cyan"))
    except Exception as e:
        console.print(f"[dim]Log not available: {e}[/dim]")

    if not poll:
        return

    # Poll until done
    console.print("\n[bold cyan]Polling...[/bold cyan]")
    poll_interval = 30
    elapsed = 0
    while status not in ("completed", "failed", "cancelled", "unknown"):
        time.sleep(poll_interval)
        elapsed += poll_interval
        try:
            run = data_service.get_workflow_status(simulation_id=simulation_id)
            status = run.status.value
        except Exception as e:
            console.print(f"  [{elapsed}s] [red]error: {e}[/red]")
            continue
        console.print(f"  [{elapsed}s] status: [yellow]{status}[/yellow]")

    _show_simulation_result(console, data_service, simulation_id, status, run.error_message)


@simulation_cli.command("cancel", help="Cancel a running simulation.")
def simulation_cancel(
    simulation_id: int = Argument(help="Simulation database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    result = data_service.cancel_workflow(simulation_id=simulation_id)
    _display(result.model_dump())


@simulation_cli.command("outputs", help="Download simulation output data as a tar.gz archive.")
def simulation_outputs(
    simulation_id: int = Argument(help="Simulation database ID."),
    dest: str | None = Option(default=None, help="Destination directory. Defaults to ./simulation_id_<ID>."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    outdir = Path(dest) if dest is not None else Path(f"simulation_id_{simulation_id}")
    archive_dir = asyncio.run(data_service.get_output_data(simulation_id=simulation_id, dest=outdir))
    from rich.console import Console

    Console().print(f"[bold green]Saved simulation outputs to:[/bold green] {archive_dir!s}")


# -- Parca commands --


@parca_cli.command("list", help="List all parca datasets.")
def parca_list(
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    datasets = data_service.get_parca_datasets()
    for ds in datasets:
        _display(ds.model_dump())


@parca_cli.command("status", help="Get the status of a parca run by its database ID.")
def parca_status(
    parca_id: int = Argument(help="Parca dataset database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    status = data_service.get_parca_status(parca_id=parca_id)
    _display(status.model_dump())


# -- Analysis commands --


@analysis_cli.command("get", help="Get an analysis spec by its database ID.")
def analysis_get(
    analysis_id: int = Argument(help="Analysis database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    analysis = data_service.get_analysis(analysis_id=analysis_id)
    _display(analysis.model_dump())


@analysis_cli.command("status", help="Get the status of an analysis run.")
def analysis_status(
    analysis_id: int = Argument(help="Analysis database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    status = data_service.get_analysis_status(analysis_id=analysis_id)
    _display(status.model_dump())


@analysis_cli.command("log", help="Get the log output of an analysis run.")
def analysis_log(
    analysis_id: int = Argument(help="Analysis database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    log = data_service.get_analysis_log(analysis_id=analysis_id)
    from rich.console import Console
    from rich.panel import Panel

    Console().print(Panel(log, title=f"Analysis Log ({analysis_id})", border_style="cyan"))


@analysis_cli.command("plots", help="Get analysis plot outputs (HTML) for an analysis run.")
def analysis_plots(
    analysis_id: int = Argument(help="Analysis database ID."),
    base_url: ApiBaseUrl = Option(default=API_BASE_URL, help="API server base URL."),
) -> None:
    data_service = get_data_service(base_url=base_url)
    plots = data_service.get_analysis_plots(analysis_id=analysis_id)
    for plot in plots:
        _display(plot.model_dump())


# -- Demo commands --


@demo_cli.command("get-data", help="Download S3 simulation outputs directly (mirrors test_outputs.py e2e test).")
def demo_get_data(
    dest: str = Option(default="./demo_outputs", help="Local destination directory for downloaded + extracted files."),
) -> None:
    """Download simulation output data directly from S3 — no running API server needed.

    Replicates the exact flow from tests/api/ecoli/test_outputs.py:
    1. Reads TEST_BUCKET_EXPERIMENT_OUTDIR from .dev_env to derive the experiment_id.
    2. Initialises a real FileServiceS3 (uses AWS creds from env).
    3. Calls the handler's _download_outputs_from_s3() to pull analyses/ + workflow_config.json.
    4. Creates a tar.gz archive and extracts it locally.

    Prerequisites:
    - AWS credentials configured (AWS_ACCESS_KEY_ID etc. in .dev_env or environment)
    - TEST_BUCKET_EXPERIMENT_OUTDIR set in .dev_env or environment
    """
    asyncio.run(_demo_get_data_async(dest))


async def _download_s3_with_progress(
    fs: FileServiceS3,
    experiment_prefix: str,
    local_cache: Path,
    console: Console,
) -> None:
    """List, filter, and download S3 objects with a Rich progress bar."""
    from sms_api.common.handlers.simulations import _ACCEPTED_ANALYSES_EXTENSIONS, _WORKFLOW_CONFIG_KEY
    from sms_api.common.storage.file_paths import S3FilePath

    # List files in S3
    with console.status("[bold cyan]Listing S3 objects...", spinner="dots"):
        analyses_prefix = S3FilePath(s3_path=Path(f"{experiment_prefix}/analyses"))
        analyses_listing = await fs.get_listing(analyses_prefix)

    # Filter to accepted extensions
    download_items: list[tuple[str, Path]] = []
    for item in analyses_listing:
        if not item.Key.endswith(_ACCEPTED_ANALYSES_EXTENSIONS):
            continue
        relative = Path(item.Key).relative_to(experiment_prefix)
        local_file = local_cache / relative
        if not local_file.exists():
            download_items.append((item.Key, local_file))

    # Add workflow_config.json
    workflow_config_key = f"{experiment_prefix}/{_WORKFLOW_CONFIG_KEY}"
    local_workflow_config = local_cache / _WORKFLOW_CONFIG_KEY
    if not local_workflow_config.exists():
        download_items.append((workflow_config_key, local_workflow_config))

    # Download with progress bar
    from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading from S3", total=len(download_items))
        for s3_key, local_file in download_items:
            local_file.parent.mkdir(parents=True, exist_ok=True)
            progress.update(task, description=f"[cyan]{Path(s3_key).name}")
            try:
                await fs.download_file(S3FilePath(s3_path=Path(s3_key)), local_file)
            except Exception:
                if _WORKFLOW_CONFIG_KEY in s3_key:
                    console.print("[dim]workflow_config.json not found, skipping[/dim]")
                else:
                    raise
            progress.advance(task)


async def _demo_get_data_async(dest: str) -> None:
    import os
    import tarfile
    from urllib.parse import urlparse

    from rich.console import Console
    from rich.panel import Panel
    from rich.tree import Tree

    console = Console()

    # 1. Derive experiment_id from TEST_BUCKET_EXPERIMENT_OUTDIR (same as test_outputs.py)
    test_outdir = os.environ.get("TEST_BUCKET_EXPERIMENT_OUTDIR", "")
    if not test_outdir:
        console.print(
            "[bold red]TEST_BUCKET_EXPERIMENT_OUTDIR is not set.[/bold red]\n"
            "[dim]Set it in assets/dev/config/.dev_env or your environment, e.g.:\n"
            "  TEST_BUCKET_EXPERIMENT_OUTDIR=s3://bucket/prefix/experiment_id/[/dim]"
        )
        raise typer.Exit(1)

    experiment_id = urlparse(test_outdir).path.strip("/").rsplit("/", 1)[-1]
    console.print(f"[bold cyan]Experiment ID:[/bold cyan] {experiment_id}")
    console.print(f"[dim]Source: {test_outdir}[/dim]\n")

    # 2. Initialise FileServiceS3 and wire into global deps
    from sms_api.common.storage.file_service_s3 import FileServiceS3
    from sms_api.config import get_settings
    from sms_api.dependencies import get_file_service, set_file_service

    settings = get_settings()
    if not settings.storage_s3_bucket or not settings.storage_s3_region:
        console.print("[bold red]S3 settings (STORAGE_S3_BUCKET, STORAGE_S3_REGION) not configured.[/bold red]")
        raise typer.Exit(1)

    console.print(f"[bold cyan]S3 bucket:[/bold cyan] {settings.storage_s3_bucket}")
    console.print(f"[bold cyan]S3 region:[/bold cyan] {settings.storage_s3_region}")
    console.print(f"[bold cyan]Output prefix:[/bold cyan] {settings.s3_output_prefix}\n")

    saved_fs = get_file_service()
    fs = FileServiceS3()
    set_file_service(fs)

    try:
        dest_path = Path(dest).resolve()
        local_cache = dest_path / experiment_id
        local_cache.mkdir(parents=True, exist_ok=True)

        experiment_prefix = f"{settings.s3_output_prefix}/{experiment_id}"
        await _download_s3_with_progress(fs, experiment_prefix, local_cache, console)

        # 3. Verify what we got
        real_files = [f for f in local_cache.rglob("*") if f.is_file()]
        if not real_files:
            console.print(f"[bold red]No files downloaded for experiment '{experiment_id}'.[/bold red]")
            console.print("[dim]Check that TEST_BUCKET_EXPERIMENT_OUTDIR points to valid simulation output.[/dim]")
            raise typer.Exit(1)

        tsv_count = sum(1 for f in real_files if f.suffix == ".tsv")
        json_count = sum(1 for f in real_files if f.suffix == ".json")

        # 4. Create tar.gz archive (same as the test's artifact saving)
        archive_path = dest_path / f"{experiment_id}.tar.gz"
        with (
            console.status("[bold cyan]Creating archive...", spinner="dots"),
            tarfile.open(archive_path, "w:gz") as tar,
        ):
            tar.add(str(local_cache), arcname=experiment_id)

        # 5. Report
        tree = Tree(f"[bold]{experiment_id}/[/bold]")
        tree.add(f"[green]{tsv_count}[/green] .tsv files")
        tree.add(f"[blue]{json_count}[/blue] .json files")
        tree.add(f"[dim]{len(real_files)} total files[/dim]")
        console.print(Panel(tree, title="Download Complete", border_style="green"))
        console.print(f"[bold green]Extracted to:[/bold green]  {local_cache}")
        console.print(f"[bold green]Archive saved:[/bold green] {archive_path}")

    finally:
        await fs.close()
        set_file_service(saved_fs)


def _display(content: Any) -> None:
    from rich.console import Console
    from rich.syntax import Syntax

    console = Console()
    import json

    if isinstance(content, str):
        console.print(content)
    else:
        formatted = json.dumps(content, indent=2, default=str)
        console.print(Syntax(formatted, "json", theme="monokai", line_numbers=False))


if __name__ == "__main__":
    main()
