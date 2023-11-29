from typing import AsyncGenerator

import pytest
from asgi_lifespan import LifespanManager
from core.config import settings
from db.seaweedfs.master import MasterCredentials
from fastapi import FastAPI
from httpx import AsyncClient
from prisma import Prisma
from prisma.types import DatasourceOverride


@pytest.fixture
async def db() -> AsyncGenerator[Prisma, None]:
    prisma_client = Prisma(datasource=DatasourceOverride(url=settings.DB_URI))
    await prisma_client.connect()
    yield prisma_client
    await prisma_client.disconnect()


@pytest.fixture
def app() -> FastAPI:
    from main import get_application

    return get_application()


@pytest.fixture
async def http_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://testserver") as client:
            yield client


@pytest.fixture(scope="session")
def seaweed_master_credentials() -> MasterCredentials:
    return MasterCredentials(url=settings.SEAWEED_MASTER_URL, volume_url=settings.SEAWEED_VOLUME_SERVER_URL)
