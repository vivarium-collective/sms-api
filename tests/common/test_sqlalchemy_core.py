import datetime
from typing import cast

import pytest
from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, MetaData, Sequence, String, Table, func, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine

meta_obj = MetaData()

users_table_seq = Sequence(name="users_seq", metadata=meta_obj)

users_table = Table(
    "users",
    meta_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("email", String, nullable=False, unique=True),
    Column("created_at", TIMESTAMP, server_default=func.now()),
)

comments_table = Table(
    "comments",
    meta_obj,
    Column("id", Integer, primary_key=True),
    Column("user_id", ForeignKey("users.id"), nullable=False),
    Column("content", String, nullable=False),
    Column("created_at", TIMESTAMP, server_default=func.now()),
)


async def create_db(async_engine: AsyncEngine) -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(meta_obj.create_all)


@pytest.mark.asyncio
async def test_async(async_db_engine: AsyncEngine) -> None:
    await create_db(async_db_engine)

    name = "John Doe"
    email = "my_email"

    async with async_db_engine.begin() as conn:
        # directly call nextval on the sequence to ensure it starts at 1 and compare current value
        result = await conn.execute(users_table_seq.next_value())
        val = result.scalar_one()
        assert val == 1
        result = await conn.execute(users_table_seq.next_value())
        val = result.scalar_one()
        assert val == 2

    async with async_db_engine.begin() as conn:
        statement = insert(users_table).values(name=name, email=email)
        print(statement)
        result = await conn.execute(statement=statement)
        assert result.rowcount == 1
        await conn.commit()

    async with async_db_engine.begin() as conn:
        query = select(users_table).where(users_table.c.name == name)
        result = await conn.execute(query)
        first_row = cast(tuple[int, str, str, datetime.datetime], result.first())
        assert first_row == (1, name, email, first_row[3])
