from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SignalRecord


class SignalRepository:
    async def add(self, db: AsyncSession, record: SignalRecord) -> SignalRecord:
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def latest(self, db: AsyncSession, engine_id: str) -> SignalRecord | None:
        result = await db.execute(select(SignalRecord).where(SignalRecord.engine_id == engine_id).order_by(SignalRecord.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def list(self, db: AsyncSession, filters: dict, limit: int, offset: int) -> list[SignalRecord]:
        stmt: Select = select(SignalRecord)
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(SignalRecord, key) == value)
        result = await db.execute(stmt.order_by(SignalRecord.created_at.desc()).limit(limit).offset(offset))
        return list(result.scalars())
