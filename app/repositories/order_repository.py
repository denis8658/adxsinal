from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderRecord


class OrderRepository:
    async def add(self, db: AsyncSession, record: OrderRecord) -> OrderRecord:
        db.add(record)
        await db.commit()
        return record

    async def signature_used(self, db: AsyncSession, idempotency_key: str) -> bool:
        return (await db.execute(select(OrderRecord.id).where(OrderRecord.idempotency_key == idempotency_key))).first() is not None
