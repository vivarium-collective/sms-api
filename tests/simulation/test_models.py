import json
import random
from pathlib import Path

import pytest

from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseServiceSQL
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDatasetRequest,
    SimulationConfig,
)


@pytest.mark.asyncio
async def test_save_request_to_mongo(database_service: DatabaseServiceSQL) -> None:
    param1_value = random.random()
    param2_value = random.random()

    for simulator in await database_service.list_simulators():
        await database_service.delete_simulator(simulator_id=simulator.database_id)

    simulator_version = await database_service.insert_simulator(
        git_commit_hash="9c3d1c8",
        git_repo_url="https://github.com/vivarium-collective/vEcoli",
        git_branch="messages",
    )
    parca_dataset_request = ParcaDatasetRequest(
        simulator_version=simulator_version,
        parca_config={"param1": 5},
    )
    parca_dataset = await database_service.insert_parca_dataset(parca_dataset_request=parca_dataset_request)

    ecoli_sim_request = EcoliSimulationRequest(
        simulator=simulator_version,
        parca_dataset_id=parca_dataset.database_id,
        variant_config={
            "named_parameters": {
                "param1": param1_value,
                "param2": param2_value,
            }
        },
    )

    # insert a document into the database
    sim: EcoliSimulation = await database_service.insert_simulation(ecoli_sim_request)
    assert sim.database_id is not None

    # reread the document from the database
    sim2 = await database_service.get_simulation(sim.database_id)
    assert sim2 is not None

    assert sim == sim2

    # delete the document from the database
    await database_service.delete_simulation(sim.database_id)
    sim3 = await database_service.get_simulation(sim.database_id)
    assert sim3 is None


@pytest.mark.asyncio
async def test_serialize_sim_config() -> None:
    assets_dir = Path(get_settings().assets_dir)
    with open(assets_dir / "sms_base_simulation_config.json") as f:
        simulation_config_raw = json.load(f)
    config = SimulationConfig(**simulation_config_raw)
    serialized = config.model_dump_json()
    # assert json.loads(serialized) == simulation_config_raw
    assert isinstance(serialized, str)
    assert isinstance(json.loads(serialized), dict)
