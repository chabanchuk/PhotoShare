from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (create_async_engine,
                                    async_sessionmaker,
                                    AsyncEngine,
                                    AsyncAttrs)

from sqlalchemy.orm import DeclarativeBase

from settings import settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class DatabaseSessionManager:
    def __init__(self, url: str):
        self._engine: AsyncEngine | None = create_async_engine(url)
        self._session_maker: async_sessionmaker = async_sessionmaker(
            autoflush=False,
            autocommit=False,
            bind=self._engine
        )

    @asynccontextmanager
    async def session(self):
        if self._session_maker is None:
            raise Exception("Session is not initialized")
        session = self._session_maker()
        try:
            yield session
        except Exception as err:
            print(err)
            await session.rollback()
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(settings.sqlalchemy_url)


async def get_db():
    async with sessionmanager.session() as session:
        try:
            yield session
        except Exception as err:
            print(err)
            await session.rollback()

