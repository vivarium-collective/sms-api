from enum import Enum

class SettingsStorageTensorstoreKvstoreDriver(str, Enum):
    FILE = "file"
    GCS = "gcs"
    S3 = "s3"

    def __str__(self) -> str:
        return str(self.value)
