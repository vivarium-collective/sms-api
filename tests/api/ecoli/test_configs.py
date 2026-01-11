import json
from pathlib import Path

import pytest

from sms_api.analysis.models import AnalysisConfig
from sms_api.simulation.models import SimulationConfig

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "configs"


@pytest.mark.asyncio
async def test_analysis_config() -> None:
    conf_path = FIXTURES_DIR / "sms_multigen_analysis.json"
    conf = AnalysisConfig.from_file(fp=conf_path)
    assert conf.analysis_options.experiment_id is not None
    assert len(conf.emitter_arg["out_dir"])


def test_load_simulation_config() -> None:
    """Test loading a simulation config from an existing asset file."""
    with open(FIXTURES_DIR / "sms_single_cell.json") as f:
        config = SimulationConfig(**json.load(f))

    # Verify key fields are loaded correctly
    assert config.experiment_id == "sms_api_single"
    assert config.generations == 1
    assert config.n_init_sims == 1
    assert config.emitter == "parquet"
    assert config.parca_options.cpus == 3
