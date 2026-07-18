from pydantic import BaseModel


class AccountResponse(BaseModel):
    session_id: str
    account_mode: str
    balance: float
    currency: str
    connected: bool
