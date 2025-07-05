import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_root(fastapi_app: FastAPI, local_base_url: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url=local_base_url) as client:
        response = await client.get("/")
        assert response.status_code == 200
        expected_response = {"docs": "http://localhost:8000/docs", "version": "0.2.2"}
        assert response.json() == expected_response
        print(response.url)
