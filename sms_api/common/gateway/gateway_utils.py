from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import HpcRun, JobType, SimulatorVersion
from sms_api.simulation.simulation_service import SimulationService


def format_version(major: int) -> str:
    return f"v{major}"


def root_prefix(major: int) -> str:
    return f"/api/{format_version(major)}"


async def dispatch_build_job(
    sim_service: SimulationService, sim_db_service: DatabaseService, simulator_version: SimulatorVersion
) -> HpcRun:
    # dispatch new build job to hpc/worker
    build_job_id = await sim_service.submit_build_image_job(simulator_version=simulator_version)
    # create and insert hpc run with ref_id pointing to simulator promary key
    return await sim_db_service.insert_hpcrun(
        job_type=JobType.BUILD_IMAGE, slurmjobid=build_job_id, ref_id=simulator_version.database_id
    )


async def get_simulation_hpcrun(simulation_id: int, db_service: DatabaseService) -> HpcRun | None:
    hpcrun = await db_service.get_hpcrun_by_ref(ref_id=simulation_id, job_type=JobType.SIMULATION)
    return hpcrun
