import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app 


@pytest.mark.asyncio
async def test_root(local_base_url: str):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=local_base_url
    ) as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    expected_response = {
        "docs": "http://localhost:8000/docs",
        "version": "0.2.2"
    }
    assert response.json() == expected_response


