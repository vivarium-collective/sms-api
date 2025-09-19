import logging
import tempfile
from pathlib import Path
import uuid

import pytest

from sms_api.config import get_settings
from sms_api.data.models import AnalysisConfig
from sms_api.data import config_service


@pytest.mark.asyncio
def test_write_json_for_slurm() -> None:
    data = {"x": {"i": 1, "j": [3, 22, 1111]}, "y": 0.22}
    with tempfile.TemporaryDirectory() as tmpdir:
        shared_dir = Path(tmpdir)
        json_path = config_service.write_json_for_slurm(data, shared_dir)

        with open(json_path, "r") as f:
            import json
            written = json.load(f)

        assert list(written.keys()) == list(data.keys())


@pytest.mark.asyncio
async def test_upload_config(analysis_config_path: Path, logger: logging.Logger, workspace_image_hash: str) -> None:
    experiment_id = f"sms_analysis_test_{str(uuid.uuid4())}"
    config = AnalysisConfig.from_file(fp=analysis_config_path)
    jobid = config_service.dispatch_job(
        experiment_id=experiment_id,
        config=config,
        env=get_settings(),
        logger=logger,
        simulator_hash=workspace_image_hash
    )
