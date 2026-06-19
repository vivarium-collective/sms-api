"""Read a simulation's emitter store (XArray/zarr or Parquet) into plain Python.

The reader is store-agnostic over fsspec URIs: ``file://`` paths work in tests,
``s3://`` paths work in production (s3fs handles credentials via the pod's role).
It has one job — turn a store URI into observable metadata and timeseries — so it
can be unit-tested without S3 or a database.
"""

from __future__ import annotations

from dataclasses import dataclass

import fsspec


@dataclass
class ObservableInfo:
    name: str
    dims: list[str]
    shape: list[int]


@dataclass
class StoreIndex:
    store: str  # "zarr" | "parquet"
    observables: list[ObservableInfo]


def detect_store_kind(store_uri: str) -> str:
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
    raise NotImplementedError("parquet store listing is added in Task 3")


def read_observables(store_uri: str, names: list[str]) -> tuple[list[float], dict[str, list[float]]]:
    """Return (time, {name: values}) for the requested observables.

    ``names=[]`` returns every observable in the store. The time axis is taken from
    the ``time`` coordinate if present, else a 0..N index.
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
            series = {n: [float(v) for v in np.asarray(ds[n].values).ravel()] for n in wanted}
        finally:
            ds.close()
        return time, series
    raise NotImplementedError("parquet reads are added in Task 3")
