import pytest_asyncio


@pytest_asyncio.fixture(scope="function")
async def local_base_url() -> str:
    return "http://localhost:8000"