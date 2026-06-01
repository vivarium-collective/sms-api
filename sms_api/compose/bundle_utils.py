"""Composite document bundle utilities using process_bigraph.bundle.

Wraps ``process_bigraph.bundle.save_bundle`` and ``load_bundle`` so that
sms-api can store and retrieve composite documents in the compact bundle
format (JSON with large arrays externalised to parquet siblings).

Currently used by the compose simulation service when writing documents
for SLURM dispatch. Falls back to direct JSON serialisation when the
document is too small to benefit from bundling.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from process_bigraph.bundle import load_bundle, save_bundle


def store_composite_document(
    document_content: str | bytes,
    outdir: str | Path | None = None,
    min_bytes: int = 1024 * 512,
) -> tuple[str, dict[str, Any]]:
    """Persist a composite document as a bundle directory.

    Args:
        document_content: Raw JSON content of the composite document.
        outdir: Target directory for the bundle. Created if needed.
            If ``None``, uses a temporary directory.
        min_bytes: Minimum estimated JSON size to externalise arrays.
            Default 512 KiB. Pass a large value to effectively disable
            array externalisation.

    Returns:
        Tuple of ``(bundle_dir_path, summary_dict)`` where *summary_dict*
        contains file sizes and array counts from ``save_bundle``.
    """
    if isinstance(document_content, bytes):
        document_content = document_content.decode("utf-8")

    document = json.loads(document_content)

    if outdir is None:
        outdir_obj: Path = Path(tempfile.mkdtemp(prefix="composite_bundle_"))
    else:
        outdir_obj = Path(outdir)
        outdir_obj.mkdir(parents=True, exist_ok=True)

    summary = save_bundle(document, str(outdir_obj), min_bytes=min_bytes)
    return str(outdir_obj), summary


def load_composite_document(bundle_dir: str | Path) -> dict[str, Any]:
    """Load a composite document from a bundle directory.

    Args:
        bundle_dir: Path to the bundle directory created by
            ``store_composite_document`` or ``save_bundle``.

    Returns:
        The resolved composite document dict (numpy arrays as lists
        by default, suitable for ``Composite(doc, core=core)``).
    """
    return load_bundle(str(bundle_dir), as_numpy=False)  # type: ignore[no-any-return]


def bundle_size_info(bundle_dir: str | Path) -> dict[str, Any]:
    """Return human-readable size info for a bundle directory.

    Args:
        bundle_dir: Path to an existing bundle directory.

    Returns:
        Dict with keys ``document_size``, ``num_arrays``,
        ``total_array_bytes``, ``total_bytes``.
    """
    doc_path = Path(bundle_dir) / "document.json"
    arrays_dir = Path(bundle_dir) / "arrays"

    doc_size = doc_path.stat().st_size if doc_path.exists() else 0

    array_sizes = {}
    total_array_bytes = 0
    if arrays_dir.is_dir():
        for f in sorted(arrays_dir.iterdir()):
            if f.is_file():
                sz = f.stat().st_size
                array_sizes[f.name] = sz
                total_array_bytes += sz

    return {
        "document_size": doc_size,
        "num_arrays": len(array_sizes),
        "total_array_bytes": total_array_bytes,
        "total_bytes": doc_size + total_array_bytes,
    }


def is_bundle_dir(path: str | Path) -> bool:
    """Check if *path* looks like a process-bigraph bundle directory."""
    p = Path(path)
    return p.is_dir() and (p / "document.json").exists()
