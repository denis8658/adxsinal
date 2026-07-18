import asyncio
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from app.core.config import Settings
from app.models import EngineInstance
from app.models.engine_state import EngineStatus, ensure_transition
from app.repositories.database import Database
from app.repositories.engine_repository import EngineRepository
from app.schemas.engine import EngineConfigPatch, EngineStartRequest
from app.services.connection_service import ConnectionService
from app.services.market_data_service import MarketDataService
from app.services.order_service import OrderService
from app.services.pocketoption_client import PocketOptionClient
from app.services.risk_service import RiskService, RiskState
from app.utils.time import utcnow


@dataclass
class EngineConfig:
    session_id: str
    asset: str
    timeframe_seconds: int
    expiration_seconds: int
    amount: float
    profile: str
    auto_execute: bool
    account_mode: str
    min_signal_score: int
    cooldown_seconds: int
    required_confirmations: int


class EngineRuntime:
    def __init__(self, config: EngineConfig):
        self.id, self.config = str(uuid.uuid4()), config
        self.status = EngineStatus.STOPPED
        self.started_at, self.stopped_at = utcnow(), None
        self.stop_event, self.finished_event = asyncio.Event(), asyncio.Event()
        self.task: asyncio.Task | None = None
        self.risk = RiskState(); self.signatures: set[str] = set(); self.confirmations = {"CALL": 0, "PUT": 0}
        self.signals_generated = self.orders_executed = self.orders_blocked = self.wins = self.losses = 0
        self.last_price = None; self.last_tick_at = None; self.last_signal = None; self.last_signal_score = 0; self.last_order_at = None
        self.active_order = False; self.error = None
        self.connection_failures = 0

    def status_payload(self) -> dict[str, Any]:
        return {"engine_id": self.id, "status": self.status, "session_id": self.config.session_id, "asset": self.config.asset, "last_price": self.last_price, "last_tick_at": self.last_tick_at, "last_signal": self.last_signal, "last_signal_score": self.last_signal_score, "last_order_at": self.last_order_at, "orders_executed": self.orders_executed, "orders_blocked": self.orders_blocked, "consecutive_losses": self.risk.consecutive_losses, "daily_profit_loss": self.risk.daily_profit_loss, "risk_locked": self.risk.locked, "connection_healthy": self.status != EngineStatus.CONNECTION_LOST, "uptime_seconds": max(0, int(((self.stopped_at or utcnow()) - self.started_at).total_seconds()))}


class EngineManager:
    def __init__(self, connections: ConnectionService, client: PocketOptionClient, database: Database, settings: Settings):
        self.connections, self.client, self.database, self.settings = connections, client, database, settings
        self.market_data, self.risk, self.orders = MarketDataService(client), RiskService(settings), OrderService(client, database)
        self.engines: dict[str, EngineRuntime] = {}; self.by_session: dict[str, str] = {}; self.lock = asyncio.Lock(); self.repo = EngineRepository()

    async def transition(self, rt: EngineRuntime, target: EngineStatus, *, risk_unlocked: bool = False) -> None:
        ensure_transition(rt.status, target, risk_unlocked=risk_unlocked)
        rt.status = target
        async with self.database.session() as db: await self.repo.event(db, rt.id, target.value)

    async def start(self, request: EngineStartRequest) -> EngineRuntime:
        from app.workers.trading_worker import TradingWorker
        sid = str(request.session_id)
        async with self.lock:
            if sid in self.by_session and self.engines[self.by_session[sid]].status != EngineStatus.STOPPED:
                raise RuntimeError("ENGINE_ALREADY_RUNNING")
            session = self.connections.get(sid)
            if not session or not await self.connections.healthy(sid): raise KeyError("SESSION_NOT_CONNECTED")
            if request.account_mode == "real" and not self.settings.allow_live_trading: raise PermissionError("LIVE_TRADING_DISABLED")
            if request.account_mode != session.account_mode: raise PermissionError("ACCOUNT_MODE_MISMATCH")
            if request.amount > self.settings.max_order_amount: raise ValueError("ORDER_AMOUNT_TOO_HIGH")
            available = await self.client.assets()
            asset_items = available.get("assets", available.get("data", []))
            names = {str(item.get("symbol", item.get("asset", ""))) if isinstance(item, dict) else str(item) for item in asset_items} if isinstance(asset_items, list) else set()
            if names and request.asset not in names: raise ValueError("ASSET_NOT_AVAILABLE")
            if request.auto_execute and self.settings.engine_mode == "live_auto" and not self.settings.allow_live_trading: raise PermissionError("LIVE_TRADING_DISABLED")
            confirmations = {"aggressive": 1, "balanced": 2, "conservative": 3}[request.profile.value]
            minimum = self.settings.min_signal_score + ({"aggressive": -2, "balanced": 0, "conservative": 2}[request.profile.value])
            cfg = EngineConfig(sid, request.asset, request.timeframe_seconds, request.expiration_seconds, request.amount, request.profile.value, request.auto_execute, request.account_mode, minimum, self.settings.order_cooldown_seconds, confirmations)
            rt = EngineRuntime(cfg); self.engines[rt.id] = rt; self.by_session[sid] = rt.id
            await self.transition(rt, EngineStatus.STARTING)
            await self.transition(rt, EngineStatus.RUNNING)
            async with self.database.session() as db: await self.repo.add_engine(db, EngineInstance(id=rt.id, session_id=sid, status=rt.status, asset=cfg.asset, configuration=asdict(cfg)))
            rt.task = asyncio.create_task(TradingWorker(rt, self).run(), name=f"trading-{rt.id}")
            return rt

    def get(self, engine_id: str) -> EngineRuntime:
        if engine_id not in self.engines: raise KeyError(engine_id)
        return self.engines[engine_id]

    async def stop(self, engine_id: str) -> EngineRuntime:
        rt = self.get(engine_id)
        if rt.status == EngineStatus.STOPPED: return rt
        if rt.status != EngineStatus.STOPPING: await self.transition(rt, EngineStatus.STOPPING)
        rt.stop_event.set()
        try: await asyncio.wait_for(rt.finished_event.wait(), timeout=max(5, self.settings.http_timeout_seconds))
        except TimeoutError:
            if rt.task: rt.task.cancel()
        await self.transition(rt, EngineStatus.STOPPED); rt.stopped_at = utcnow(); self.by_session.pop(rt.config.session_id, None)
        return rt

    async def pause(self, engine_id: str) -> EngineRuntime:
        rt = self.get(engine_id); await self.transition(rt, EngineStatus.PAUSED); return rt

    async def resume(self, engine_id: str) -> EngineRuntime:
        rt = self.get(engine_id)
        if not await self.connections.healthy(rt.config.session_id): raise ConnectionError("CONNECTION_UNAVAILABLE")
        if rt.risk.locked: raise PermissionError("RISK_LOCKED")
        await self.transition(rt, EngineStatus.RUNNING); return rt

    async def unlock_risk(self, engine_id: str) -> EngineRuntime:
        rt = self.get(engine_id)
        if rt.status != EngineStatus.RISK_LOCKED and not rt.risk.locked: raise ValueError("RISK_NOT_LOCKED")
        self.risk.unlock(rt.risk); await self.transition(rt, EngineStatus.RUNNING, risk_unlocked=True)
        async with self.database.session() as db: await self.repo.risk_event(db, rt.id, "RISK_UNLOCKED")
        return rt

    def update_config(self, engine_id: str, patch: EngineConfigPatch) -> EngineRuntime:
        rt = self.get(engine_id)
        if rt.active_order: raise RuntimeError("ACTIVE_ORDER")
        values = patch.model_dump(exclude_none=True)
        if "amount" in values and values["amount"] > self.settings.max_order_amount: raise ValueError("ORDER_AMOUNT_TOO_HIGH")
        if "profile" in values: values["profile"] = values["profile"].value
        for key, value in values.items(): setattr(rt.config, key, value)
        return rt

    async def shutdown(self) -> None:
        await asyncio.gather(*(self.stop(x) for x in list(self.engines) if self.engines[x].status not in {EngineStatus.STOPPED}), return_exceptions=True)
