from enum import StrEnum

import numpy
import numpy as np
import orjson
import polars as pl


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


def serialize_dataframe(df: pl.DataFrame) -> dict[str, SerializedArray]:
    dataframe = {}
    cols = df.columns
    for i, col in enumerate(df.iter_columns()):
        dataframe[cols[i]] = SerializedArray(col.to_numpy())
    return dataframe


def test_serialize_dataframe() -> None:
    df = pl.DataFrame(dict(zip(["x", "y", "z"], [numpy.random.random((1111,)) for _ in range(3)])))
    data = serialize_dataframe(df)
    print(data)
