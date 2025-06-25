import asyncio

from sms_api.simulation.simulation_service import SimulationServiceHpc

if __name__ == "__main__":
    hpc_service = SimulationServiceHpc()
    if hpc_service is not None:
        latest_commit_path = "assets/latest_commit.txt"
        latest_commit = asyncio.run(hpc_service.get_latest_commit_hash())
        with open(latest_commit_path, "w") as f:
            f.write(latest_commit)
    else:
        raise Exception("Could not initialize HPC service to retrieve the latest commit.")
