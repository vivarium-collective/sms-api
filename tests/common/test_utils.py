import pytest

from sms_api.common.utils import unique_id, get_uuid


@pytest.mark.asyncio
async def test_unique_id() -> None:
    dataid = "test"
    unique = unique_id(dataid)
    assert len(unique.replace(f"{dataid}_", "")) == (4 + 1 + 8)  # (tag + sep + date)
    print(unique)


@pytest.mark.asyncio
async def test_get_uuid() -> None:
    scope = "analysis"
    data_id = "myexperiment_id"
    uid = get_uuid(scope)
    print()

    uid2 = get_uuid(scope, data_id)
    print()