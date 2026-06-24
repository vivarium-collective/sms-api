"""Read a simulation's emitter store (XArray/zarr or Parquet) into plain Python.

The reader is store-agnostic over fsspec URIs: ``file://`` paths work in tests,
``s3://`` paths work in production (s3fs handles credentials via the pod's role).
It has one job — turn a store URI into observable metadata and timeseries — so it
can be unit-tested without S3 or a database.

Read performance (per review):
- The Parquet path uses **Polars** with **column projection** — listing reads
  only the schema + the parquet footer row count (no column data), and fetching
  reads only the requested columns + ``time``, so only the requested data leaves
  S3.
- ``read_observables`` supports **decimation** (``stride`` / ``max_points``)
  applied *before* materialization — a lazy row-slice on the Polars side and an
  ``isel`` on the zarr side — so a long multi-generation run never serializes
  millions of points it doesn't need.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import fsspec


@dataclass
class ObservableInfo:
    name: str
    dims: list[str]
    shape: list[int]


@dataclass
class StoreIndex:
    store: Literal["zarr", "parquet"]
    observables: list[ObservableInfo]


def detect_store_kind(store_uri: str) -> Literal["zarr", "parquet"]:
    """Return 'zarr' if the store is a zarr group (has a .zgroup/.zattrs), else 'parquet'."""
    fs, path = fsspec.core.url_to_fs(store_uri)
    if fs.exists(f"{path}/.zgroup") or fs.exists(f"{path}/zarr.json"):
        return "zarr"
    return "parquet"


def _effective_stride(n: int, stride: int, max_points: int | None) -> int:
    """Combine an explicit ``stride`` with a ``max_points`` cap into one step >= 1.

    ``max_points`` wins when it implies a coarser step than ``stride`` (so the
    response never exceeds ``max_points`` points); otherwise ``stride`` is used.
    """
    step = max(1, stride)
    if max_points is not None and max_points >= 1 and n > 0:
        step = max(step, math.ceil(n / max_points))
    return step


def list_observables(store_uri: str) -> StoreIndex:
    """Open the emitter store and return its observable variables (name, dims, shape).

    Metadata-only: the Parquet path reads the schema and the footer row count, not
    any column data.
    """
    kind = detect_store_kind(store_uri)
    if kind == "zarr":
        import xarray as xr

        ds = xr.open_zarr(store_uri)
        try:
            obs = [
                ObservableInfo(name=str(name), dims=[str(d) for d in var.dims], shape=[int(s) for s in var.shape])
                for name, var in ds.data_vars.items()
            ]
        finally:
            ds.close()
        return StoreIndex(store="zarr", observables=obs)

    import polars as pl

    lf = pl.scan_parquet(store_uri)
    names = lf.collect_schema().names()
    nrows = int(lf.select(pl.len()).collect().item())
    obs = [ObservableInfo(name=str(c), dims=["time"], shape=[nrows]) for c in names if c != "time"]
    return StoreIndex(store="parquet", observables=obs)


def _sanitize(value: float) -> float | None:
    """Convert NaN/Inf to None for JSON-safe output."""
    if math.isfinite(value):
        return value
    return None


def read_observables(
    store_uri: str,
    names: list[str],
    *,
    stride: int = 1,
    max_points: int | None = None,
) -> tuple[Literal["zarr", "parquet"], list[float], dict[str, list[float | None]]]:
    """Return (store_kind, time, {name: values}) for the requested observables.

    ``names=[]`` returns every observable in the store. The time axis is taken from
    the ``time`` coordinate if present, else a 0..N index.

    ``stride`` returns every Nth point; ``max_points`` caps the total points (and
    overrides ``stride`` when it implies a coarser step). Decimation is applied
    *before* materialization — a lazy row-slice (Parquet) / ``isel`` (zarr) — so
    only the kept points are read and serialized.

    Raises ``KeyError`` if a requested observable is absent, and ``ValueError`` if
    an observable's values are not a 1-D timeseries. Non-finite float values
    (NaN, ±Inf) are sanitized to ``None``.
    """
    kind = detect_store_kind(store_uri)
    if kind == "zarr":
        import numpy as np
        import xarray as xr

        ds = xr.open_zarr(store_uri)
        try:
            wanted = names or [str(n) for n in ds.data_vars]
            missing = [n for n in wanted if n not in ds.data_vars]
            if missing:
                raise KeyError(f"observables not in store: {missing}")
            n = int(ds["time"].shape[0]) if "time" in ds.coords else int(ds[wanted[0]].shape[0])
            step = _effective_stride(n, stride, max_points)
            row_slice = slice(None, None, step)
            if "time" in ds.coords:
                time_da = ds["time"]
                raw_time = np.asarray(time_da.isel({time_da.dims[0]: row_slice}).values).ravel()
                time = [float(t) for t in raw_time]
            else:
                time = [float(i) for i in range(0, n, step)]
            series: dict[str, list[float | None]] = {}
            for nm in wanted:
                var = ds[nm]
                if var.ndim != 1 or var.shape[0] != n:
                    raise ValueError(
                        f"observable {nm!r} is not a 1-D timeseries (shape {tuple(var.shape)}); "
                        "multi-dimensional observables are not supported"
                    )
                arr = np.asarray(var.isel({var.dims[0]: row_slice}).values)
                series[nm] = [_sanitize(float(v)) for v in arr]
        finally:
            ds.close()
        return kind, time, series

    import polars as pl

    lf = pl.scan_parquet(store_uri)
    schema_names = lf.collect_schema().names()
    wanted = names or [c for c in schema_names if c != "time"]
    missing = [n for n in wanted if n not in schema_names]
    if missing:
        raise KeyError(f"observables not in store: {missing}")
    has_time = "time" in schema_names
    nrows = int(lf.select(pl.len()).collect().item())
    step = _effective_stride(nrows, stride, max_points)
    cols = ["time", *wanted] if has_time else list(wanted)
    df = lf.select(cols).gather_every(step).collect()
    time = [float(t) for t in df["time"].to_list()] if has_time else [float(i) for i in range(0, nrows, step)]
    series_p: dict[str, list[float | None]] = {n: [_sanitize(float(v)) for v in df[n].to_list()] for n in wanted}
    return kind, time, series_p
