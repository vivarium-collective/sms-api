import asyncio
from pathlib import Path

from sms_api.config import get_settings
from sms_api.dependencies import get_simulation_service


async def write_latest_commit() -> str:
    hpc_service = get_simulation_service()
    if hpc_service is not None:
        assets_dir = Path(get_settings().assets_dir)
        latest_commit_path = assets_dir / "simulation" / "model" / "latest_commit.txt"
        latest_commit = await hpc_service.get_latest_commit_hash()
        with open(latest_commit_path, "w") as f:
            f.write(latest_commit)
        return latest_commit
    else:
        raise Exception("Could not initialize HPC service to retrieve the latest commit.")


if __name__ == "__main__":
    asyncio.run(write_latest_commit())
