import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from sms_api.common.gateway.models import ServerMode
from sms_api.version import __version__

server_urls = [ServerMode.DEV, ServerMode.PROD]
current_version = __version__


@pytest.mark.asyncio
async def test_home_template(fastapi_app: FastAPI, local_base_url: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url=local_base_url) as client:
        response = await client.get("/")
        assert response.status_code == 200
        html = response.text

        assert "Available Applications" in html
        assert "/ws" in html
        # for name in ["Antibiotics", "Biomanufacturing", "Single Cell"]:
        for name in ["Single Cell"]:
            assert name in html


@pytest.mark.asyncio
async def test_version(fastapi_app: FastAPI, local_base_url: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url=local_base_url) as client:
        response = await client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data == current_version
