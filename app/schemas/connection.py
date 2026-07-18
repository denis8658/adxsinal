from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.validators import validate_ssid


class SessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    ssid: str = Field(min_length=12, max_length=8192, repr=False)
    persistent_connection: bool = True
    auto_reconnect: bool = True
    connect_after_init: bool = True

    @field_validator("ssid")
    @classmethod
    def valid_ssid(cls, value: str) -> str:
        return validate_ssid(value)


class SessionResponse(BaseModel):
    status: str
    session_id: UUID
    account_mode: str
    balance: float
    currency: str
    external_api_connected: bool
    engine_running: bool
    created_at: datetime


class DisconnectResponse(BaseModel):
    status: str = "disconnected"
    session_id: UUID
    engine_running: bool = False
