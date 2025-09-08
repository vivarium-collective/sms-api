import tempfile
from pathlib import Path

import pytest

from sms_api.data.utils import write_json_for_slurm


@pytest.mark.asyncio
def test_write_json_for_slurm() -> None:
    data = {"x": {"i": 1, "j": [3, 22, 1111]}, "y": 0.22}
    with tempfile.TemporaryDirectory() as tmpdir:
        shared_dir = Path(tmpdir)
        json_path = write_json_for_slurm(data, shared_dir, "test.json")

        with open(json_path) as f:
            import json

            written = json.load(f)

        assert list(written.keys()) == list(data.keys())


@pytest.mark.asyncio
async def test_upload_config() -> None:
    pass
