import random

import pytest
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.results import InsertOneResult


@pytest.mark.asyncio
async def test_mongo(mongo_test_collection: AsyncCollection) -> None:
    param1_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    param2_value = random.random()  # noqa: S311 Standard pseudo-random generators are not suitable for cryptographic purposes
    # get a timestamp as an integer
    doc_to_save = {
        "parameters": {
            "named_parameters": {
                "param1": param1_value,
                "param2": param2_value,
            }
        }
    }

    # insert a document into the database
    result: InsertOneResult = await mongo_test_collection.insert_one(doc_to_save)
    assert result.acknowledged

    # reread the document from the database
    document = await mongo_test_collection.find_one({"_id": result.inserted_id})
    assert document is not None

    assert document["parameters"] == doc_to_save["parameters"]
    assert document["_id"] == result.inserted_id

    # delete the document from the database
    del_result = await mongo_test_collection.delete_one({"_id": result.inserted_id})
    assert del_result.deleted_count == 1
