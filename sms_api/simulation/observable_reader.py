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
