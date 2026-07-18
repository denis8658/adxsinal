import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.utils.time import utcnow


class Base(DeclarativeBase):
    pass


class EngineSession(Base):
    __tablename__ = "engine_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ssid_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    account_mode: Mapped[str] = mapped_column(String(16), default="demo")
    state: Mapped[str] = mapped_column(String(24), default="connected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EngineInstance(Base):
    __tablename__ = "engine_instances"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("engine_sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    asset: Mapped[str] = mapped_column(String(64))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SignalRecord(Base):
    __tablename__ = "signal_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engine_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    asset: Mapped[str] = mapped_column(String(64), index=True)
    direction: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    classification: Mapped[str] = mapped_column(String(24), index=True)
    decision: Mapped[str] = mapped_column(String(40), index=True)
    price: Mapped[float] = mapped_column(Float)
    call_score: Mapped[int] = mapped_column(Integer)
    put_score: Mapped[int] = mapped_column(Integer)
    signature: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    blocks: Mapped[list[str]] = mapped_column(JSON, default=list)
    indicators: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    order_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    data_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class OrderRecord(Base):
    __tablename__ = "order_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    engine_id: Mapped[str] = mapped_column(String(36), index=True)
    asset: Mapped[str] = mapped_column(String(64), index=True)
    direction: Mapped[str] = mapped_column(String(8))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RiskEvent(Base):
    __tablename__ = "risk_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engine_id: Mapped[str] = mapped_column(String(36), index=True)
    reason: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EngineEvent(Base):
    __tablename__ = "engine_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    engine_id: Mapped[str] = mapped_column(String(36), index=True)
    event: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
