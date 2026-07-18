from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class StrategyProfile(StrEnum):
    aggressive = "aggressive"
    balanced = "balanced"
    conservative = "conservative"


class EngineStartRequest(BaseModel):
    session_id: UUID
    asset: str = Field(pattern=r"^[A-Za-z0-9_\-]{3,64}$")
    timeframe_seconds: int = Field(ge=1, le=3600)
    expiration_seconds: int = Field(ge=5, le=86400)
    amount: float = Field(gt=0)
    profile: StrategyProfile = StrategyProfile.balanced
    auto_execute: bool = False
    account_mode: str = Field(default="demo", pattern="^(demo|real)$")

    @model_validator(mode="after")
    def expiration_not_shorter(self) -> "EngineStartRequest":
        if self.expiration_seconds < self.timeframe_seconds:
            raise ValueError("expiration_seconds deve ser maior ou igual ao timeframe")
        return self


class EngineStartResponse(EngineStartRequest):
    status: str = "started"
    engine_id: UUID
    started_at: datetime


class EngineIdRequest(BaseModel):
    engine_id: UUID


class RiskUnlockRequest(EngineIdRequest):
    confirmation: str


class EngineStopResponse(BaseModel):
    status: str = "stopped"
    engine_id: UUID
    signals_generated: int
    orders_executed: int
    orders_blocked: int
    wins: int
    losses: int
    stopped_at: datetime


class EngineConfigPatch(BaseModel):
    amount: float | None = Field(default=None, gt=0)
    timeframe_seconds: int | None = Field(default=None, ge=1, le=3600)
    expiration_seconds: int | None = Field(default=None, ge=5, le=86400)
    min_signal_score: int | None = Field(default=None, ge=0, le=100)
    asset: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_\-]{3,64}$")
    cooldown_seconds: int | None = Field(default=None, ge=0, le=3600)
    profile: StrategyProfile | None = None
    auto_execute: bool | None = None
