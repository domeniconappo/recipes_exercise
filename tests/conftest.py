
import pytest
import pytest_asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sqlmodel import SQLModel

from app.main import app
from app.database import get_db
from app.config import settings


# ---------------------------------------------------------
# Engine + schema (session-scoped)
# ---------------------------------------------------------

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    """
    Creates/drops tables once per test session.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        future=True,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------
# Session factory
# ---------------------------------------------------------

@pytest_asyncio.fixture(scope="session", loop_scope="session")
def session_factory(engine):
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


# ---------------------------------------------------------
# Per-test DB session (for unit tests)
# ---------------------------------------------------------

# @pytest_asyncio.fixture(scope="session", loop_scope="session")
# async def db(session_factory):
#     async with session_factory() as session:
#         yield session
#         await session.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(engine):
    """
    Bare DB session for service-level tests.
    Tables are truncated before each test.
    """
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(table.delete())

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

# ---------------------------------------------------------
# Automatic TRUNCATE between every test
# ---------------------------------------------------------

@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def cleanup_db(engine):
    yield
    async with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            await conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))


# ---------------------------------------------------------
# FastAPI test client (NOW SESSION-SCOPED)
# ---------------------------------------------------------

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def client(session_factory):
    """
    One shared AsyncClient for the entire test session.
    This + the pytest config above puts everything on the same event loop.
    """
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as async_client:
        yield async_client

    app.dependency_overrides.clear()
