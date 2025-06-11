import random

import pytest
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.results import InsertOneResult

from sms_api.simulation.models import EcoliSimulationRequest, ParcaDataset, SimulationSpec, VariantSpec


@pytest.mark.asyncio
async def test_save_request_to_mongo(mongo_test_collection: AsyncCollection) -> None:
    param1_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    param2_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    param3_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    param4_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    # get a timestamp as an integer

    parca_dataset = ParcaDataset(
        id="test_dataset_id",
        name="test_dataset",
        remote_archive_path="http://example.com/parca",
        description="Test dataset for E. coli simulations",
        hash="abc123hash",
    )
    variant_spec = VariantSpec(
        variant_id="test_variant_id",
        name="test_variant",
        description="Test variant for E. coli simulations",
        parameters={"param1": param1_value, "param2": param2_value},
    )
    simulation_spec = SimulationSpec(
        parca_dataset=parca_dataset,
        variant_spec=variant_spec,
        named_parameters={"param3": param3_value, "param4": param4_value},
    )
    ecoli_sim_request = EcoliSimulationRequest(
        simulation_spec=simulation_spec,
        simulator_version="1.0.0",
    )

    # insert a document into the database
    result: InsertOneResult = await mongo_test_collection.insert_one(ecoli_sim_request.model_dump())
    assert result.acknowledged

    # reread the document from the database
    document = await mongo_test_collection.find_one({"_id": result.inserted_id})
    assert document is not None
    saved_request = EcoliSimulationRequest.model_validate(document)

    assert saved_request.simulation_spec == ecoli_sim_request.simulation_spec
    assert saved_request.simulator_version == ecoli_sim_request.simulator_version
    assert saved_request.deep_hash == ecoli_sim_request.deep_hash

    # delete the document from the database
    del_result = await mongo_test_collection.delete_one({"_id": result.inserted_id})
    assert del_result.deleted_count == 1
