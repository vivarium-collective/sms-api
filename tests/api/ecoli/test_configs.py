import json
from pathlib import Path

import pytest

from sms_api.analysis.models import AnalysisConfig
from sms_api.config import get_settings
from sms_api.simulation.models import SimulationConfig


@pytest.mark.asyncio
async def test_analysis_config() -> None:
    assets_dir = Path(get_settings().assets_dir)
    conf_path = assets_dir / "sms_multigen_analysis.json"
    conf = AnalysisConfig.from_file(fp=conf_path)
    assert conf.analysis_options.experiment_id is not None
    assert len(conf.emitter_arg["out_dir"])


def test_load_simulation_config() -> None:
    """Test loading a simulation config from an existing asset file."""
    assets_dir = Path(get_settings().assets_dir)
    with open(assets_dir / "sms_single_cell.json") as f:
        config = SimulationConfig(**json.load(f))

    # Verify key fields are loaded correctly
    assert config.experiment_id == "sms_api_single"
    assert config.generations == 1
    assert config.n_init_sims == 1
    assert config.emitter == "parquet"
    assert config.parca_options.cpus == 3
