import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel


class AsyncDatabase:
    """Minimal async database wrapper that provides an async context manager get_db
    and an initialize() method that creates tables via SQLModel.metadata.create_all.

    This is intentionally lightweight to avoid changing the rest of the codebase which
    expects a db_helper with get_db() method.
    """

    def __init__(self, database_url: str) -> None:
        self.DATABASE_URL = database_url
        self.engine = create_async_engine(self.DATABASE_URL, echo=False, future=True)
        self.AsyncSessionLocal = async_sessionmaker(self.engine, expire_on_commit=False)
        self.inited = False

    async def initialize(self) -> None:
        # Create tables if they don't exist
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        self.inited = True

    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        if not self.inited:
            await self.initialize()
        async with self.AsyncSessionLocal() as session:
            yield session

    # For compatibility with code expecting a synchronous .get_db as contextmanager name,
    # callers should use `async with db_helper.get_db()`.
