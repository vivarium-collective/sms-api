import json
import pathlib
from collections.abc import Collection
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy
import numpy as np
import orjson


@dataclass
class BiocycData:
    obj_id: str
    org_id: str
    data: dict[str, Any]
    request: dict[str, Collection[str]]
    dest_dirpath: pathlib.Path | None = None

    @property
    def filepath(self) -> pathlib.Path:
        dest_fp = self.dest_dirpath or pathlib.Path("assets/biocyc")
        return dest_fp / f"{self.obj_id}.json"

    def to_dict(self) -> dict[str, str | dict[str, Any] | dict[str, str] | pathlib.Path | None]:
        return asdict(self)

    def export(self, fp: pathlib.Path | None = None) -> None:
        try:
            exp = self.to_dict()
            fp = fp or self.filepath
            with open(fp, "w") as f:
                json.dump(exp, f, indent=4)
            print(f"Successfully wrote: {fp}")
        except OSError:
            print(f"Could not write for {self.obj_id}")


class OutputDomain(StrEnum):
    ANALYSIS = "analysis"
    PARQUET = "history"
    STATE = "daughter_states"
    PARAMETERS = "parca"


class SerializedArray:
    __slots__ = ("_value", "shape")

    def __init__(self, arr: numpy.ndarray) -> None:
        self._value = self.serialize(arr)

    def serialize(self, arr: numpy.ndarray) -> bytes:
        self.shape = arr.shape
        return orjson.dumps(numpy.ravel(arr, order="C").tolist())

    def deserialize(self) -> numpy.ndarray:
        arr: np.ndarray = np.array(orjson.loads(self._value))
        return arr.reshape(self.shape)

    @property
    def value(self) -> numpy.ndarray:
        return self.deserialize()

    @value.setter
    def value(self, value: np.ndarray) -> None:
        self._value = self.serialize(value)
