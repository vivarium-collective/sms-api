from pathlib import Path

import pytest

from sms_api.data.models import AnalysisConfig


@pytest.mark.asyncio
async def test_analysis_config() -> None:
    conf_path = Path("/Users/alexanderpatrie/sms/vEcoli/configs/sms_multigen_analysis.json")
    conf = AnalysisConfig.from_file(fp=conf_path)
    assert conf.analysis_options.experiment_id is not None
    assert len(conf.emitter_arg["out_dir"])
