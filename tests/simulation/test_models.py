import random

import pytest

from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDatasetRequest,
)
from sms_api.simulation.simulation_database import SimulationDatabaseService


@pytest.mark.asyncio
async def test_save_request_to_mongo(database_service: SimulationDatabaseService) -> None:
    param1_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    param2_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes

    simulator_version = await database_service.get_or_insert_simulator(
        version="1.0.0", docker_image="test_docker_image", docker_hash="test_docker_hash"
    )
    parca_dataset_request = ParcaDatasetRequest(
        simulator_version=simulator_version,
        parca_config={"param1": 5},
    )
    parca_dataset = await database_service.get_or_insert_parca_dataset(parca_dataset_request=parca_dataset_request)

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
