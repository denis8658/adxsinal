from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import connections, engines
from app.core.exceptions import ExternalAPIError
from app.schemas.connection import DisconnectResponse, SessionCreate, SessionResponse
from app.services.connection_service import ConnectionService
from app.services.engine_manager import EngineManager

router = APIRouter(prefix="/api/v1/connection", tags=["connection"])


@router.post("/session", response_model=SessionResponse, status_code=201)
async def create_session(body: SessionCreate, service: ConnectionService = Depends(connections)):
    try:
        context, balance = await service.create(body)
        return {"status": "connected" if context.connected else "initialized", "session_id": context.id, "account_mode": context.account_mode, "balance": float(balance.get("balance", balance.get("amount", 0))), "currency": str(balance.get("currency", "USD")), "external_api_connected": context.connected, "engine_running": False, "created_at": context.created_at}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"code": "SESSION_ALREADY_EXISTS", "message": str(exc)}) from exc
    except ExternalAPIError as exc:
        raise HTTPException(status_code=502, detail={"code": "POCKETOPTION_CONNECTION_FAILED", "message": "Não foi possível conectar à API externa."}) from exc


@router.delete("/session/{session_id}", response_model=DisconnectResponse)
async def disconnect_session(session_id: str, service: ConnectionService = Depends(connections), manager: EngineManager = Depends(engines)):
    try:
        engine_id = manager.by_session.get(session_id)
        if engine_id: await manager.stop(engine_id)
        await service.disconnect(session_id)
        return {"session_id": session_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "Sessão não encontrada."}) from exc
