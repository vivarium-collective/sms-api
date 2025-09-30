import pytest

from sms_api.config import get_settings


@pytest.mark.skipif(int(get_settings().dev_mode) != 1, reason="Not in local mode")
@pytest.mark.asyncio
async def test_get_simulation_data_client() -> None:
    from app.client_wrapper import ClientWrapper

    client = ClientWrapper(base_url="http://localhost:8888")
    resp = await client.get_simulation_data(
        experiment_id="sms_multigeneration",
        lineage=6,
        generation=1,
        obs=["bulk", "listeners__rnap_data__termination_loss"],
    )
    assert sorted(resp.columns) == sorted(["bulk", "time", "listeners__rnap_data__termination_loss"])
    print(resp)
