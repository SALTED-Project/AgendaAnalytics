from typing import AsyncGenerator

from core.config import settings
from db.file_repository import HttpFileRepository
from db.seaweedfs.file_repository import SeaweedFileRepository
from db.seaweedfs.master import Master, MasterCredentials

from prisma import Prisma
from prisma.types import DatasourceOverride



async def db_client() -> AsyncGenerator[Prisma, None]:
    client = Prisma(datasource=DatasourceOverride(url=settings.DB_URI))
    await client.connect()
    yield client
    await client.disconnect()


def seaweed_credentials() -> MasterCredentials:
    return MasterCredentials(url=settings.SEAWEED_MASTER_URL, volume_url=settings.SEAWEED_VOLUME_SERVER_URL)


def file_repository() -> HttpFileRepository:
    return SeaweedFileRepository(Master(seaweed_credentials()))


