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
from typing import Any

RESULTS_DIR = Path(os.environ.get("PBG_RESULTS_DIR", "/experiment/output"))


def _build_core() -> Any:
    """A process-bigraph Core (process-bigraph's own base types) with pbg-emitters'
    link classes registered.

    ``Composite`` requires a ``core`` (``bigraph_schema.edge.Edge.__init__`` raises
    ``"must provide a core"`` when it's ``None``) — the baseline construction is
    ``allocate_core()`` + ``process_bigraph.register_types()``, the same pair
    ``process_bigraph``'s own package init uses. ``pbg-emitters`` ships in every
    compose container (``container_def.py``) but a document's
    ``{"address": "local:ParquetEmitter", ...}`` step only resolves if the Core
    it's built against has that address registered, so it's added the same way
    v2ecoli's own ``build_core()`` does (``v2ecoli/core.py``) — any uploaded
    document that wires a pbg-emitters step (zarr/parquet, matching what
    ``observable_reader.py`` expects) resolves the same way it would in a
    workspace that authored it.
    """
    from bigraph_schema import allocate_core
    from process_bigraph import register_types

    core = register_types(allocate_core())

    try:
        from pbg_emitters import ParquetEmitter

        core.register_link("ParquetEmitter", ParquetEmitter)
    except ImportError:
        pass  # [parquet] extra not installed in this image
    try:
        from pbg_emitters import SQLiteEmitter

        core.register_link("SQLiteEmitter", SQLiteEmitter)
    except ImportError:
        pass  # [sqlite] extra not installed in this image
    try:
        from pbg_emitters import XArrayEmitter

        core.register_link("XArrayEmitter", XArrayEmitter)
    except ImportError:
        pass  # [xarray] extra not installed in this image
    return core


def run(input_file: str, steps: int, results_dir: Path = RESULTS_DIR) -> Path:
    """Load a ``.pbg`` document, run it ``steps`` times, write ``final_state.json``.

    Any pbg-emitters step the document itself wires (``local:ParquetEmitter`` etc.)
    resolves via ``_build_core()`` and writes its own zarr/parquet output alongside
    this snapshot — ``final_state.json`` stays as the always-present fallback so a
    document with no emitter step still produces *something* under ``results_dir``.
    """
    from process_bigraph import Composite  # imported lazily so tests can stub it

    results_dir.mkdir(parents=True, exist_ok=True)
    document = json.loads(Path(input_file).read_text())
    composite = Composite(document, core=_build_core())  # full-path local:! addresses resolve via importlib
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
