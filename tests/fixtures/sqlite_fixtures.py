import tempfile
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sms_api.dependencies import get_database_service, get_db_engine, set_database_service, set_db_engine
from sms_api.simulation.database_service import DatabaseService, DatabaseServiceSQL
from sms_api.simulation.tables_orm import create_db


@pytest_asyncio.fixture(scope="function")
async def async_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        sqlite_url = f"sqlite+aiosqlite:///{tmpdir}/test.db"
        engine = create_async_engine(url=sqlite_url, echo=True)
        prev_engine: AsyncEngine | None = get_db_engine()
        try:
            set_db_engine(engine)
            await create_db(engine)
            yield engine
        finally:
            set_db_engine(prev_engine)
            await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def database_service(async_db_engine: AsyncEngine) -> AsyncGenerator[DatabaseService, None]:
    saved_database_service = get_database_service()
    database_service = DatabaseServiceSQL(async_engine=async_db_engine)
    set_database_service(database_service)
    yield database_service
    set_database_service(saved_database_service)
