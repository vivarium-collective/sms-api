import random

import pytest

from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    ParcaDatasetRequest,
)


@pytest.mark.asyncio
async def test_save_request_to_mongo(database_service: DatabaseService) -> None:
    param1_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    param2_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes

    for simulator in await database_service.list_simulators():
        await database_service.delete_simulator(simulator_id=simulator.database_id)

    simulator_version = await database_service.insert_simulator(
        git_commit_hash="9c3d1c8",
        git_repo_url="https://github.com/CovertLab/vEcoli",
        git_branch="master",
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
