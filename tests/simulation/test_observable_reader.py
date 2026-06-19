from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from sms_api.simulation.observable_reader import (
    StoreIndex,
    detect_store_kind,
    list_observables,
    read_observables,
)


def _write_fixture_zarr(tmp_path: Path) -> str:
    """Write a tiny XArray zarr store and return its file:// URI."""
    ds = xr.Dataset(
        data_vars={
            "mass": ("time", np.array([1.0, 2.0, 3.0])),
            "volume": ("time", np.array([0.1, 0.2, 0.3])),
        },
        coords={"time": np.array([0.0, 1.0, 2.0])},
    )
    store_path = tmp_path / "store.zarr"
    ds.to_zarr(store_path, mode="w")
    return f"file://{store_path}"


def test_detect_store_kind_zarr(tmp_path: Path) -> None:
    uri = _write_fixture_zarr(tmp_path)
    assert detect_store_kind(uri) == "zarr"


def test_list_observables_zarr(tmp_path: Path) -> None:
    uri = _write_fixture_zarr(tmp_path)
    idx = list_observables(uri)
    assert isinstance(idx, StoreIndex)
    assert idx.store == "zarr"
    names = {o.name for o in idx.observables}
    assert names == {"mass", "volume"}
    mass = next(o for o in idx.observables if o.name == "mass")
    assert mass.dims == ["time"]
    assert mass.shape == [3]


def test_read_observables_zarr_selected(tmp_path: Path) -> None:
    uri = _write_fixture_zarr(tmp_path)
    time, series = read_observables(uri, names=["mass"])
    assert time == [0.0, 1.0, 2.0]
    assert series == {"mass": [1.0, 2.0, 3.0]}


def test_read_observables_zarr_all(tmp_path: Path) -> None:
    uri = _write_fixture_zarr(tmp_path)
    time, series = read_observables(uri, names=[])
    assert set(series) == {"mass", "volume"}
    assert series["volume"] == [0.1, 0.2, 0.3]


def _write_fixture_parquet(tmp_path: Path) -> str:
    df = pd.DataFrame({"time": [0.0, 1.0, 2.0], "mass": [1.0, 2.0, 3.0], "volume": [0.1, 0.2, 0.3]})
    p = tmp_path / "store.parquet"
    df.to_parquet(p)
    return f"file://{p}"


def test_detect_store_kind_parquet(tmp_path: Path) -> None:
    uri = _write_fixture_parquet(tmp_path)
    assert detect_store_kind(uri) == "parquet"


def test_list_observables_parquet(tmp_path: Path) -> None:
    uri = _write_fixture_parquet(tmp_path)
    idx = list_observables(uri)
    assert idx.store == "parquet"
    assert {o.name for o in idx.observables} == {"mass", "volume"}  # time excluded


def test_read_observables_parquet(tmp_path: Path) -> None:
    uri = _write_fixture_parquet(tmp_path)
    time, series = read_observables(uri, names=["volume"])
    assert time == [0.0, 1.0, 2.0]
    assert series == {"volume": [0.1, 0.2, 0.3]}
