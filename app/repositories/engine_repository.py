from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EngineEvent, EngineInstance, EngineSession, RiskEvent


class EngineRepository:
    async def add_session(self, db: AsyncSession, session: EngineSession) -> None:
        db.add(session); await db.commit()

    async def add_engine(self, db: AsyncSession, engine: EngineInstance) -> None:
        db.add(engine); await db.commit()

    async def event(self, db: AsyncSession, engine_id: str, event: str, details: dict | None = None) -> None:
        db.add(EngineEvent(engine_id=engine_id, event=event, details=details or {})); await db.commit()

    async def risk_event(self, db: AsyncSession, engine_id: str, reason: str, details: dict | None = None) -> None:
        db.add(RiskEvent(engine_id=engine_id, reason=reason, details=details or {})); await db.commit()
