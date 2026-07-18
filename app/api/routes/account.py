from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import connections
from app.services.connection_service import ConnectionService

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get("/{session_id}")
async def account(session_id: str, service: ConnectionService = Depends(connections)):
    context = service.get(session_id)
    if not context: raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Sessão não encontrada."})
    balance = await service.client.balance()
    return {"session_id": session_id, "account_mode": context.account_mode, "balance": balance.get("balance", 0), "currency": balance.get("currency", "USD"), "connected": context.connected}
