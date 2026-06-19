"""Read a simulation's emitter store (XArray/zarr or Parquet) into plain Python.

The reader is store-agnostic over fsspec URIs: ``file://`` paths work in tests,
``s3://`` paths work in production (s3fs handles credentials via the pod's role).
It has one job — turn a store URI into observable metadata and timeseries — so it
can be unit-tested without S3 or a database.
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


def list_observables(store_uri: str) -> StoreIndex:
    """Open the emitter store and return its observable variables (name, dims, shape)."""
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
    import pandas as pd

    df = pd.read_parquet(store_uri)
    cols = [c for c in df.columns if c != "time"]
    obs = [ObservableInfo(name=str(c), dims=["time"], shape=[len(df)]) for c in cols]
    return StoreIndex(store="parquet", observables=obs)


def _sanitize(value: float) -> float | None:
    """Convert NaN/Inf to None for JSON-safe output."""
    if math.isfinite(value):
        return value
    return None


def read_observables(
    store_uri: str, names: list[str]
) -> tuple[Literal["zarr", "parquet"], list[float], dict[str, list[float | None]]]:
    """Return (store_kind, time, {name: values}) for the requested observables.

    ``names=[]`` returns every observable in the store. The time axis is taken from
    the ``time`` coordinate if present, else a 0..N index.

    Raises ``ValueError`` if an observable's values are not a 1-D timeseries.
    Non-finite float values (NaN, ±Inf) are sanitized to ``None``.
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
            if "time" in ds.coords:
                time = [float(t) for t in np.asarray(ds["time"].values).ravel()]
            else:
                first = ds[wanted[0]]
                time = [float(i) for i in range(int(first.shape[0]))]
            series: dict[str, list[float | None]] = {}
            for n in wanted:
                arr = np.asarray(ds[n].values)
                if arr.ndim != 1 or arr.shape[0] != len(time):
                    raise ValueError(
                        f"observable {n!r} is not a 1-D timeseries (shape {arr.shape}); "
                        "multi-dimensional observables are not supported"
                    )
                series[n] = [_sanitize(float(v)) for v in arr]
        finally:
            ds.close()
        return kind, time, series

    import pandas as pd

    df = pd.read_parquet(store_uri)
    wanted = names or [str(c) for c in df.columns if c != "time"]
    missing = [n for n in wanted if n not in df.columns]
    if missing:
        raise KeyError(f"observables not in store: {missing}")
    time = [float(t) for t in df["time"].tolist()] if "time" in df.columns else [float(i) for i in range(len(df))]
    series_p: dict[str, list[float | None]] = {n: [_sanitize(float(v)) for v in df[n].tolist()] for n in wanted}
    return kind, time, series_p
