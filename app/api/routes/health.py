from fastapi import APIRouter, Request
from sqlalchemy import text

from app.utils.time import utcnow

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    database = "connected"
    try:
        async with request.app.state.database.session() as db: await db.execute(text("SELECT 1"))
    except Exception: database = "unavailable"
    external = "reachable"
    try: await request.app.state.client.connection_stats()
    except Exception: external = "unreachable"
    active = sum(x.status not in {"STOPPED", "ERROR"} for x in request.app.state.engines.engines.values())
    return {"status": "healthy" if database == "connected" else "degraded", "external_api": external, "database": database, "active_engines": active, "timestamp": utcnow()}


@router.get("/ready")
async def ready(request: Request):
    async with request.app.state.database.session() as db: await db.execute(text("SELECT 1"))
    return {"status": "ready", "timestamp": utcnow()}


@router.get("/live")
async def live(): return {"status": "alive", "timestamp": utcnow()}
