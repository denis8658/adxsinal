from enum import StrEnum

from pydantic import BaseModel, Field


class Direction(StrEnum):
    CALL = "CALL"
    PUT = "PUT"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    SUBMITTING = "SUBMITTING"
    ACCEPTED = "ACCEPTED"
    ACTIVE = "ACTIVE"
    WON = "WON"
    LOST = "LOST"
    DRAW = "DRAW"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class OrderPlace(BaseModel):
    asset: str
    direction: Direction
    amount: float = Field(gt=0)
    duration_seconds: int = Field(gt=0)
