"""Generic process-bigraph runner executed inside the compose container.

CLI contract (fixed by sms-api's ``_build_run_command``)::

    python run_pbg.py <input-file> -o <outdir> -n <steps>

Writes results into ``/experiment/output`` (the bind-mounted, zipped dir).
The ``-o`` value is accepted for CLI compatibility but output always lands in
``RESULTS_DIR`` so it matches sms-api's ``zip -r ../results.zip`` collection.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

RESULTS_DIR = Path(os.environ.get("PBG_RESULTS_DIR", "/experiment/output"))


def run(input_file: str, steps: int, results_dir: Path = RESULTS_DIR) -> Path:
    """Load a ``.pbg`` document, run it ``steps`` times, write ``final_state.json``."""
    from process_bigraph import Composite  # imported lazily so tests can stub it

    results_dir.mkdir(parents=True, exist_ok=True)
    document = json.loads(Path(input_file).read_text())
    composite = Composite(document)  # full-path local:! addresses resolve via importlib
    composite.run(steps)
    out = results_dir / "final_state.json"
    out.write_text(json.dumps(composite.serialize_state(), default=str))
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("-o", "--output", default=str(RESULTS_DIR))
    parser.add_argument("-n", "--steps", type=int, default=1)
    args = parser.parse_args(argv)
    run(args.input_file, args.steps)


if __name__ == "__main__":
    main()
