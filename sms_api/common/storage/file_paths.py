from pathlib import Path

from pydantic import BaseModel


class HPCFilePath(BaseModel):
    """Represents a file path on the HPC remote system.

    Configuration via JSON in .env files:
        HPC_IMAGE_BASE_PATH={"remote_path": "/home/FCAM/svc_vivarium/test/images"}

    Attributes:
        remote_path: (``pathlib.Path``)
    """

    remote_path: Path

    def __str__(self) -> str:
        return str(self.remote_path)

    @property
    def parent(self) -> "HPCFilePath":
        return HPCFilePath(remote_path=self.remote_path.parent)

    @property
    def name(self) -> str:
        return self.remote_path.name

    def __truediv__(self, other: str) -> "HPCFilePath":
        if "{" in other or "}" in other or ":" in other or '"' in other:
            raise ValueError(f"HPCFilePath can not composing paths from json strings, unexpected arg '{other}'")
        return HPCFilePath(remote_path=self.remote_path / other)


class ScratchFilePath(BaseModel):
    """Represents a local scratch file path.

    Configuration via JSON in .env files:
        SCRATCH_DIR={"local_path": "/tmp/scratch"}
    """

    local_path: Path

    def __str__(self) -> str:
        return str(self.local_path)

    @property
    def parent(self) -> "ScratchFilePath":
        return ScratchFilePath(local_path=self.local_path.parent)

    @property
    def name(self) -> str:
        return self.local_path.name

    def __truediv__(self, other: str) -> "ScratchFilePath":
        if "{" in other or "}" in other or ":" in other or '"' in other:
            raise ValueError(f"ScratchFilePath can not composing paths from json strings, unexpected arg '{other}'")
        return ScratchFilePath(local_path=self.local_path / other)


class S3FilePath(BaseModel):
    """Represents an S3 file path without the bucket.

    Configuration via JSON in .env files:
        S3_DATA_PATH={"s3_path": "/path"}
    """

    # bucket: str
    s3_path: Path

    def __str__(self) -> str:
        return str(self.s3_path)

    @property
    def parent(self) -> "S3FilePath":
        return S3FilePath(s3_path=self.s3_path.parent)

    @property
    def name(self) -> str:
        return self.s3_path.name

    def __truediv__(self, other: str) -> "S3FilePath":
        if "{" in other or "}" in other or ":" in other or '"' in other:
            raise ValueError(f"S3FilePath can not composing paths from json strings, unexpected arg '{other}'")
        return S3FilePath(s3_path=self.s3_path / other)
