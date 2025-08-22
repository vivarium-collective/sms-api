import polars as pl

from sms_api.data.models import SerializedArray


def serialize_dataframe(df: pl.DataFrame) -> dict[str, SerializedArray]:
    dataframe = {}
    cols = df.columns
    for i, col in enumerate(df.iter_columns()):
        dataframe[cols[i]] = SerializedArray(col.to_numpy())
    return dataframe
