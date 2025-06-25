import os
from pathlib import Path

DEFAULT_CHUNK_IDS = [400, 800, 1200, 1600, 2000, 2400, 2529]


def read_latest_commit() -> str:
    with open("assets/latest_commit.txt") as f:
        return f.read().strip()


def get_single_simulation_chunks_dirpath(remote_dir_root: Path) -> Path:
    experiment_dirname = str(remote_dir_root).split("/")[-1]
    return Path(
        os.path.join(
            remote_dir_root,
            "history",
            f"'experiment_id={experiment_dirname}",
            "'variant=0'",
            "'lineage_seed=0'",
            "'generation=1'",
            "'agent_id=0'",
        )
    )
