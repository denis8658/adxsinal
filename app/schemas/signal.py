from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    direction: str | None
    score: int
    classification: str
    decision: str
    price: float
    reasons: list[str]
    blocks: list[str]
    timestamp: datetime
