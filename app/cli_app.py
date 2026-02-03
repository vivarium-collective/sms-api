import asyncio
from pathlib import Path
from pprint import pp
from typing import Any

import httpx
import typer
from typer import Argument, Option

from app.app_data_service import get_data_service, SimulationType, SUPPORTED_CONFIGS


cli = typer.Typer()
show_cli = typer.Typer()
simulation_cli = typer.Typer()
simulation_cli.add_typer(show_cli, name="show")
simulator_cli = typer.Typer()
simulator_cli.add_typer(show_cli, name="show")
cli.add_typer(simulation_cli, name="simulation")
cli.add_typer(simulator_cli, name="simulator")
cli.add_typer(show_cli, name="show")


def display(content: Any) -> None:
    print()
    pp(content)
    print()


@show_cli.command("latest", rich_help_panel="vEcoli Versions")
def simulator() -> None:
    data_service = get_data_service()
    simulator = data_service.get_simulator()
    display(simulator.model_dump())


@show_cli.command(rich_help_panel="Simulators")
def simulators() -> None:
    data_service = get_data_service()
    simulators = data_service.show_simulators()
    for sim in simulators:
        display(sim.model_dump())


@show_cli.command("simulation", rich_help_panel="Simulations")
def show_simulation(simulation_id: int = Argument(help="Simulation Database Id")) -> None:
    """
    Retrieve an uploaded simulation specification, along with the
     corresponding simulation workflow config JSON used to run the
     job.
    """
    data_service = get_data_service()
    simulation = data_service.get_workflow(simulation_id=simulation_id)
    display(simulation.model_dump())


@show_cli.command("simulations", rich_help_panel="Simulations")
def show_simulations(simulation_id: int) -> None:
    data_service = get_data_service()
    simulations = data_service.show_workflows()
    display([sim.model_dump() for sim in simulations])


@simulation_cli.command("run", rich_help_panel="Simulations")
def run_simulation(
    experiment_id: str = Argument(help="Unique experiment identifier"),
    simulator_id: int = Argument(help="Database Id of the Simulator linked to the version of vEcoli you wish to use."),
    simulation_type: SimulationType = Argument(
        help="Type of simulation to run corresponding to simulation config "
        "JSON names. See user documentation for more details."
    ),
    # TODO: generalize and enable deployment-specific vals
    generations: int = Option(default=1, help="Number of generations to run per lineage(seed). Defaults to 8."),
    seeds: int = Option(default=3, help="Number of lineages (seeds). Defaults to 3."),
    description: str | None = Option(default=None, help="Custom description/metadata for simulation workflow run."),
    run_parameter_calculator: bool = Option(
        default=False,
        help="If True, run the parameter calculator prior to the "
        "simulation step in the overall workflow. Warning: "
        "setting this to True will cause the overall "
        "workflow job runtime to increase substantially.",
    ),
) -> None:
    """
    Run a simulation workflow whose steps include: parca -> simulation -> analysis.
    """
    if simulation_type not in SUPPORTED_CONFIGS:
        raise ValueError(f"Invalid simulation type. Expected one of: {SUPPORTED_CONFIGS}; Got: {simulation_type}")
    params = httpx.QueryParams(
        experiment_id=experiment_id,
        simulator_id=simulator_id,
        simulation_config_filename=f"{simulation_type}.json",
        num_generations=generations or 8,
        num_seeds=seeds or 4,
        description=description or f"sim{simulator_id}-{experiment_id}; {generations} Generations; {seeds} Seeds",
        run_parca=run_parameter_calculator or False,
    )
    data_service = get_data_service()
    simulation = data_service.run_workflow(params=params)
    display(simulation.model_dump())


@simulation_cli.command("status", rich_help_panel="Simulations")
def simulation_status(simulation_id: int) -> None:
    data_service = get_data_service()
    log = data_service.get_workflow_log(simulation_id=simulation_id)
    print(f"Workflow log for simulation_id: {simulation_id}:\n{log}")
    try:
        status_update = data_service.get_workflow_status(simulation_id=simulation_id)
        print(f"Workflow Status: {status_update.upper()}")
    except:
        pass


@simulation_cli.command("outputs", rich_help_panel="Simulations")
def outputs(simulation_id: int, dest: str | None = None) -> None:
    data_service = get_data_service()
    outdir = Path(dest) if dest is not None else Path(f"simulation_id_{simulation_id}")
    archive_dir = asyncio.run(data_service.get_output_data(simulation_id=simulation_id, dest=outdir))
    display(f"Saved simulation outputs to: {archive_dir!s}!")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()