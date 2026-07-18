from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import database
from app.repositories.database import Database
from app.repositories.signal_repository import SignalRepository

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])
repo = SignalRepository()


def serialize(x):
    return {"id": x.id, "engine_id": x.engine_id, "session_id": x.session_id, "asset": x.asset, "direction": x.direction, "score": max(x.call_score, x.put_score), "call_score": x.call_score, "put_score": x.put_score, "classification": x.classification, "decision": x.decision, "price": x.price, "reasons": x.reasons, "blocks": x.blocks, "timestamp": x.created_at}


@router.get("")
async def list_signals(engine_id: str | None = None, asset: str | None = None, direction: str | None = None, classification: str | None = None, decision: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0), dbs: Database = Depends(database)):
    filters = {"engine_id": engine_id, "asset": asset, "direction": direction, "classification": classification, "decision": decision}
    async with dbs.session() as db:
        records = await repo.list(db, filters, limit, offset)
    records = [x for x in records if (not date_from or x.created_at >= date_from) and (not date_to or x.created_at <= date_to)]
    return [serialize(x) for x in records]


@router.get("/latest/{engine_id}")
async def latest(engine_id: str, dbs: Database = Depends(database)):
    async with dbs.session() as db: record = await repo.latest(db, engine_id)
    if not record: raise HTTPException(status_code=404, detail={"code": "SIGNAL_NOT_FOUND", "message": "Nenhum sinal encontrado."})
    return serialize(record)
