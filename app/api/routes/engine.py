from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import engines
from app.schemas.engine import EngineConfigPatch, EngineIdRequest, EngineStartRequest, RiskUnlockRequest
from app.services.engine_manager import EngineManager
from app.utils.time import utcnow

router = APIRouter(prefix="/api/v1/engine", tags=["engine"])


def _error(exc: Exception) -> HTTPException:
    code = str(exc).strip("'")
    statuses = {"ENGINE_ALREADY_RUNNING": 409, "LIVE_TRADING_DISABLED": 403, "ACCOUNT_MODE_MISMATCH": 403, "RISK_LOCKED": 409, "ACTIVE_ORDER": 409}
    return HTTPException(status_code=statuses.get(code, 404 if isinstance(exc, KeyError) else 400), detail={"code": code, "message": "Operação do motor não pôde ser concluída."})


@router.post("/start", status_code=202)
async def start(body: EngineStartRequest, request: Request, manager: EngineManager = Depends(engines)):
    try:
        rt = await manager.start(body)
        return {"status": "started", "engine_id": rt.id, **body.model_dump(mode="json"), "started_at": rt.started_at, "started_by": request.client.host if request.client else "unknown"}
    except (RuntimeError, KeyError, PermissionError, ValueError) as exc: raise _error(exc) from exc


@router.post("/stop")
async def stop(body: EngineIdRequest, manager: EngineManager = Depends(engines)):
    try:
        rt = await manager.stop(str(body.engine_id))
        return {"status": "stopped", "engine_id": rt.id, "signals_generated": rt.signals_generated, "orders_executed": rt.orders_executed, "orders_blocked": rt.orders_blocked, "wins": rt.wins, "losses": rt.losses, "stopped_at": rt.stopped_at}
    except (KeyError, RuntimeError) as exc: raise _error(exc) from exc


@router.post("/pause")
async def pause(body: EngineIdRequest, manager: EngineManager = Depends(engines)):
    try: return {"status": "paused", "engine_id": (await manager.pause(str(body.engine_id))).id}
    except Exception as exc: raise _error(exc) from exc


@router.post("/resume")
async def resume(body: EngineIdRequest, manager: EngineManager = Depends(engines)):
    try: return {"status": "running", "engine_id": (await manager.resume(str(body.engine_id))).id}
    except Exception as exc: raise _error(exc) from exc


@router.post("/unlock-risk")
async def unlock(body: RiskUnlockRequest, manager: EngineManager = Depends(engines)):
    if body.confirmation != "UNLOCK_RISK": raise HTTPException(status_code=400, detail={"code": "INVALID_CONFIRMATION", "message": "Confirmação inválida."})
    try: return {"status": "unlocked", "engine_id": (await manager.unlock_risk(str(body.engine_id))).id, "unlocked_at": utcnow()}
    except Exception as exc: raise _error(exc) from exc


@router.get("/status/{engine_id}")
async def engine_status(engine_id: str, manager: EngineManager = Depends(engines)):
    try: return manager.get(engine_id).status_payload()
    except KeyError as exc: raise _error(exc) from exc


@router.get("/config/{engine_id}")
async def get_config(engine_id: str, manager: EngineManager = Depends(engines)):
    try: return asdict(manager.get(engine_id).config)
    except KeyError as exc: raise _error(exc) from exc


@router.patch("/config/{engine_id}")
async def update_config(engine_id: str, body: EngineConfigPatch, manager: EngineManager = Depends(engines)):
    try: return asdict(manager.update_config(engine_id, body).config)
    except Exception as exc: raise _error(exc) from exc
