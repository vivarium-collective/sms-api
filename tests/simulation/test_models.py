import json
from pathlib import Path
from typing import Any

import pytest

from sms_api.config import get_settings
from sms_api.simulation.models import (
    BaseModel,
    SimulationConfig,
    trim_attributes,
)


@pytest.mark.asyncio
async def test_serialize_sim_config() -> None:
    assets_dir = Path(get_settings().assets_dir)
    with open(assets_dir / "sms_single_cell.json") as f:
        simulation_config_raw = json.load(f)
    config = SimulationConfig(**simulation_config_raw)
    serialized = config.model_dump_json()
    assert isinstance(serialized, str)
    assert isinstance(json.loads(serialized), dict)
    # Verify round-trip preserves key fields
    deserialized = json.loads(serialized)
    assert deserialized["experiment_id"] == simulation_config_raw["experiment_id"]


@pytest.mark.asyncio
async def test_trim_attributes() -> None:
    class A(BaseModel):
        x: float
        k: float | None = None
        args: list[float] | None = None

        def model_post_init(self, context: Any, /) -> None:
            trim_attributes(self)

    a = A(x=11.11)
    assert a.model_dump() == {"x": 11.11}
