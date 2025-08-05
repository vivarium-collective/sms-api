from pathlib import Path

from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import HpcRun, JobType

REPO_DIR = Path(__file__).parent.parent.parent.parent.absolute()
PINNED_OUTDIR = REPO_DIR / "out" / "sms_single"


def get_simulation_outdir(experiment_id: str) -> Path:
    outdir = REPO_DIR / "out" / experiment_id
    if not outdir.exists():
        raise FileNotFoundError(f"{outdir} does not exist. Try running a simulation first.")
    return outdir


def format_version(major: int) -> str:
    return f"v{major}"


def root_prefix(major: int) -> str:
    return f"/api/{format_version(major)}"


async def get_simulation_hpcrun(simulation_id: int, db_service: DatabaseService) -> HpcRun | None:
    hpcrun = await db_service.get_hpcrun_by_ref(ref_id=simulation_id, job_type=JobType.SIMULATION)
    return hpcrun


def format_marimo_appname(appname: str) -> str:
    """Capitalizes and separates appnames(module names) if needed."""
    if "_" in appname:
        return appname.replace("_", " ").title()
    else:
        return appname.replace(appname[0], appname[0].upper())
