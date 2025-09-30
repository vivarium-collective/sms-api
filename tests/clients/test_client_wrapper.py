import httpx
import pytest


async def locally_running_server(url: str = "http://localhost:8888") -> bool:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=1.0)
            return resp.status_code < 500
    except (httpx.ConnectError, httpx.ReadTimeout):
        return False


@pytest.mark.asyncio
async def test_get_simulation_data_client() -> None:
    from app.client_wrapper import ClientWrapper

    if await locally_running_server():
        client = ClientWrapper(base_url="http://localhost:8888")
        resp = await client.get_simulation_data(
            experiment_id="sms_multigeneration",
            lineage=6,
            generation=1,
            obs=["bulk", "listeners__rnap_data__termination_loss"],
        )
        assert sorted(resp.columns) == sorted(["bulk", "time", "listeners__rnap_data__termination_loss"])
        print(resp)
