import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(app_client: AsyncClient, postgres_url: str) -> None:
    response = await app_client.get("/")
    assert response.status_code == 200
    expected_response = {"docs": "http://localhost:8000/docs", "version": "0.2.2"}
    assert response.json() == expected_response
    print(response.url)
    print(f"POSTGRES URL: {postgres_url}")
