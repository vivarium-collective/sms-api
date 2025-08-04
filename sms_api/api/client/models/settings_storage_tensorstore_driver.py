from enum import Enum


class SettingsStorageTensorstoreDriver(str, Enum):
    N5 = "n5"
    ZARR = "zarr"
    ZARR3 = "zarr3"

    def __str__(self) -> str:
        return str(self.value)
