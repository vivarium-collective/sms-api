import pytest
from httpx import ASGITransport, AsyncClient

from sms_api.api.main import app
from sms_api.data.models import AnalysisRequest
from sms_api.simulation.database_service import DatabaseService


@pytest.mark.asyncio
async def test_run_analysis(
    base_router: str, analysis_request: AnalysisRequest, database_service: DatabaseService
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/analyses", json=analysis_request.model_dump())
        response.raise_for_status()
        data = response.json()
        assert isinstance(data["config"]["analysis_options"]["experiment_id"], list)


@pytest.mark.asyncio
async def test_get_analysis(
    base_router: str, analysis_request: AnalysisRequest, database_service: DatabaseService
) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(f"{base_router}/analyses", json=analysis_request.model_dump())
        response.raise_for_status()
        analysis_response = response.json()
        db_id = analysis_response["database_id"]

        fetch_response = await client.get(f"/analyses/fetch/{db_id}")
        fetch_response.raise_for_status()
        assert fetch_response.json() == analysis_response
