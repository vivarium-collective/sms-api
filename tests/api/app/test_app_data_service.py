"""Integration tests for E2EDataService - requires live server connection.

These tests connect to a real API server and may fail due to:
- Server not reachable
- Gateway timeout (504) when HPC file gathering exceeds nginx/ingress timeout

To run: pytest tests/api/app/test_app_data_service.py -v -m integration
To skip: pytest tests/api/app/test_app_data_service.py -v -m "not integration"
"""

import os
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from app.app_data_service import BaseUrl, E2EDataService, get_data_service

# --- Configuration ---
TEST_BASE_URL = BaseUrl.LOCAL_8080
TEST_TIMEOUT = 30000  # 30k seconds client-side (server gateway may timeout sooner)
TEST_SIMULATION_ID = 96

# Set to True to run integration tests even when they might timeout
RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"


def server_is_reachable() -> bool:
    """Check if the test server is reachable."""
    try:
        response = httpx.get(f"{TEST_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


# --- Fixtures ---


@pytest_asyncio.fixture
async def simulation_id_lite() -> int:
    return 5


@pytest_asyncio.fixture
async def simulation_id_medium() -> int:
    return 6


@pytest_asyncio.fixture
async def simulation_id_heavy() -> int:
    return 7


@pytest_asyncio.fixture
async def data_service() -> E2EDataService:
    return get_data_service(base_url=TEST_BASE_URL, timeout=TEST_TIMEOUT)


# --- Integration Tests (require live server) ---


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(not RUN_INTEGRATION_TESTS, reason="Set RUN_INTEGRATION_TESTS=true to run")
@pytest.mark.skipif(not server_is_reachable(), reason="Test server not reachable")
async def test_submit_stream_output_data(data_service: E2EDataService, simulation_id_heavy: int) -> None:
    """Integration test: requires live server and may timeout due to gateway limits."""
    try:
        streaming_response = await data_service.submit_stream_output_data(simulation_id=simulation_id_heavy)
        assert isinstance(streaming_response, set)
    except httpx.HTTPError as e:
        if "504" in str(e):
            pytest.xfail("Gateway timeout - server-side proxy timeout too short for HPC file gathering")
        raise


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(not RUN_INTEGRATION_TESTS, reason="Set RUN_INTEGRATION_TESTS=true to run")
@pytest.mark.skipif(not server_is_reachable(), reason="Test server not reachable")
async def test_get_output_data(data_service: E2EDataService) -> None:
    """
    Integration test: downloads simulation outputs from live server.

    NOTE: This test may fail with 504 Gateway Timeout if the server's
    nginx/ingress gateway timeout is shorter than the time needed to
    gather files from HPC. To fix, increase server-side proxy timeout:

    Nginx: proxy_read_timeout 3600s;
    K8s Ingress: nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    """
    dest = Path("test_downloads")
    try:
        archive_dir = await data_service.get_output_data(
            simulation_id=TEST_SIMULATION_ID,
            dest=dest,
            timeout=TEST_TIMEOUT,
        )
        assert isinstance(archive_dir, Path)
        assert archive_dir.exists()
    except httpx.HTTPError as e:
        if "504" in str(e):
            pytest.xfail("Gateway timeout - server-side proxy timeout too short for HPC file gathering")
        raise
