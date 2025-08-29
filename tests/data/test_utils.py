import numpy
import polars as pl
import pytest

from sms_api.data.utils import serialize_dataframe


@pytest.mark.asyncio
async def test_serialize_dataframe() -> None:
    df = pl.DataFrame(dict(zip(["x", "y", "z"], [numpy.random.random((1111,)) for _ in range(3)])))
    data = serialize_dataframe(df)
    print(data)
