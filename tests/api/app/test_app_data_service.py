from pathlib import Path

import pytest
import pytest_asyncio

from app.app_data_service import E2EDataService, get_data_service


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
    return get_data_service()


@pytest.mark.asyncio
async def test_submit_stream_output_data(data_service: E2EDataService, simulation_id_heavy: int) -> None:
    streaming_response = await data_service.submit_stream_output_data(simulation_id=simulation_id_heavy)
    assert isinstance(streaming_response, set)


@pytest.mark.asyncio
async def test_get_output_data(data_service: E2EDataService, simulation_id_heavy: int) -> None:
    dest = Path("test_downloads")
    archive_dir = await data_service.get_output_data(simulation_id=simulation_id_heavy, dest=dest)
    assert isinstance(archive_dir, Path)
