from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.models import Base


class Database:
    def __init__(self, settings: Settings):
        url = settings.normalized_database_url
        options = {"pool_pre_ping": True}
        if url.startswith("sqlite+"):
            options["connect_args"] = {"timeout": 30}
        else:
            options.update(pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=1800)
        self.engine = create_async_engine(url, **options)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_all(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()

    def session(self) -> AsyncSession:
        return self.sessions()
