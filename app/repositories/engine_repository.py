from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import EngineEvent, EngineInstance, EngineSession, RiskEvent


class EngineRepository:
    async def add_session(self, db: AsyncSession, session: EngineSession) -> None:
        db.add(session); await db.commit()

    async def upsert_session(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        ssid_hash: str,
        account_mode: str,
        state: str,
        created_at: datetime,
    ) -> EngineSession:
        session = await db.scalar(select(EngineSession).where(EngineSession.ssid_hash == ssid_hash))
        if session is None:
            session = EngineSession(id=session_id, ssid_hash=ssid_hash)
            db.add(session)
        session.account_mode = account_mode
        session.state = state
        session.created_at = created_at
        try:
            await db.commit()
        except IntegrityError:
            # Outra réplica pode ter inserido o mesmo hash entre o SELECT e o
            # COMMIT. Nesse caso, reutilize o registro vencedor.
            await db.rollback()
            session = await db.scalar(select(EngineSession).where(EngineSession.ssid_hash == ssid_hash))
            if session is None:
                raise
            session.account_mode = account_mode
            session.state = state
            session.created_at = created_at
            await db.commit()
        return session

    async def update_session_state(self, db: AsyncSession, session_id: str, state: str) -> None:
        session = await db.get(EngineSession, session_id)
        if session is None:
            return
        session.state = state
        await db.commit()

    async def add_engine(self, db: AsyncSession, engine: EngineInstance) -> None:
        db.add(engine); await db.commit()

    async def event(self, db: AsyncSession, engine_id: str, event: str, details: dict | None = None) -> None:
        db.add(EngineEvent(engine_id=engine_id, event=event, details=details or {})); await db.commit()

    async def risk_event(self, db: AsyncSession, engine_id: str, reason: str, details: dict | None = None) -> None:
        db.add(RiskEvent(engine_id=engine_id, reason=reason, details=details or {})); await db.commit()
