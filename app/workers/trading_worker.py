import asyncio
from datetime import timedelta

from app.models import SignalRecord
from app.models.engine_state import EngineStatus
from app.repositories.signal_repository import SignalRepository
from app.services.confluence_service import ConfluenceService
from app.services.indicator_service import IndicatorService
from app.services.market_data_service import MarketDataService
from app.services.signal_service import SignalService
from app.utils.time import utcnow


class TradingWorker:
    def __init__(self, runtime, manager):
        self.runtime, self.manager = runtime, manager
        self.indicators = IndicatorService()
        self.confluence = ConfluenceService()
        self.signals = SignalService()
        self.repo = SignalRepository()

    async def run(self) -> None:
        rt = self.runtime
        try:
            while not rt.stop_event.is_set():
                if rt.status in {EngineStatus.PAUSED, EngineStatus.RISK_LOCKED}:
                    await self._wait(); continue
                if not await self.manager.connections.healthy(rt.config.session_id):
                    rt.connection_failures += 1
                    if rt.status != EngineStatus.CONNECTION_LOST:
                        await self.manager.transition(rt, EngineStatus.CONNECTION_LOST)
                    if rt.connection_failures >= 3:
                        await self.manager.transition(rt, EngineStatus.ERROR)
                        rt.error = "CONNECTION_UNAVAILABLE"
                        rt.stop_event.set()
                    if not rt.stop_event.is_set(): await self._wait()
                    continue
                rt.connection_failures = 0
                if rt.status == EngineStatus.CONNECTION_LOST:
                    await self.manager.transition(rt, EngineStatus.RUNNING)
                await self.iteration()
                await self._wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            rt.error = type(exc).__name__
            if rt.status not in {EngineStatus.STOPPING, EngineStatus.STOPPED}:
                await self.manager.transition(rt, EngineStatus.ERROR)
        finally:
            rt.finished_event.set()

    async def _wait(self) -> None:
        try:
            await asyncio.wait_for(self.runtime.stop_event.wait(), timeout=self.manager.settings.engine_loop_interval_ms / 1000)
        except TimeoutError:
            pass

    async def iteration(self) -> None:
        rt, cfg = self.runtime, self.runtime.config
        candles = await self.manager.market_data.candles(cfg.asset, cfg.timeframe_seconds)
        data_ts = self.manager.market_data.data_timestamp(candles)
        stale = utcnow() - data_ts > timedelta(seconds=max(cfg.timeframe_seconds * 3, 15))
        values = self.indicators.calculate(candles)
        result = self.confluence.evaluate(values, stale=stale, connection_healthy=True)
        direction, score, classification = self.signals.choose(result, cfg.min_signal_score, self.manager.settings.min_direction_score_difference)
        reasons = result.reasons_call if direction == "CALL" else result.reasons_put if direction == "PUT" else []
        risk_blocks = self.manager.risk.validate(rt.risk, amount=cfg.amount, data_stale=stale, latency_ms=self.manager.client.last_latency_ms, connection_healthy=True, active_order=rt.active_order, cooldown_seconds=cfg.cooldown_seconds)
        if self.manager.settings.min_payout > 0:
            payouts = await self.manager.client.payouts()
            raw_payout = payouts.get(cfg.asset, payouts.get("payout", 0))
            if isinstance(raw_payout, dict): raw_payout = raw_payout.get("payout", raw_payout.get("value", 0))
            if float(raw_payout or 0) < self.manager.settings.min_payout: risk_blocks.append("Payout abaixo do mínimo")
        if rt.risk.locked and rt.status == EngineStatus.RUNNING:
            await self.manager.transition(rt, EngineStatus.RISK_LOCKED)
            async with self.manager.database.session() as db:
                await self.manager.repo.risk_event(db, rt.id, rt.risk.reason or "RISK_LOCKED")
        blocks = result.blocks + risk_blocks
        decision = "NO_SIGNAL"
        signature = None
        if direction:
            rt.confirmations[direction] = rt.confirmations.get(direction, 0) + 1
            rt.confirmations["PUT" if direction == "CALL" else "CALL"] = 0
            signature = self.signals.signature(cfg.asset, direction, cfg.timeframe_seconds, data_ts, str(values["adx_fast"].get("cross", 0)), values["structure"]["last_pivot_timestamp"])
            if blocks: decision = "BLOCKED_BY_RISK" if risk_blocks else "BLOCKED_BY_CONNECTION"
            elif rt.confirmations[direction] < cfg.required_confirmations: decision = "WAITING_CONFIRMATION"
            elif not cfg.auto_execute or self.manager.settings.engine_mode == "signal_only": decision = "SIGNAL_ONLY"
            elif signature in rt.signatures: decision = "BLOCKED_BY_COOLDOWN"
            else:
                if not await self.manager.connections.healthy(cfg.session_id):
                    rt.orders_blocked += 1; decision = "BLOCKED_BY_CONNECTION"
                else:
                    rt.active_order = True
                    order = await self.manager.orders.place(rt.id, cfg.asset, direction, cfg.amount, cfg.expiration_seconds, signature)
                    rt.active_order = False
                    rt.signatures.add(signature)
                    if order.status in {"ACCEPTED", "ACTIVE"}:
                        rt.orders_executed += 1; self.manager.risk.record_order(rt.risk); decision = "ORDER_SUBMITTED"; rt.last_order_at = utcnow()
                    else: rt.orders_blocked += 1; decision = "BLOCKED_BY_RISK"
        else:
            rt.confirmations = {"CALL": 0, "PUT": 0}
        rt.signals_generated += 1
        rt.last_price = float(candles[-1]["close"]); rt.last_tick_at = data_ts
        rt.last_signal, rt.last_signal_score = direction, score
        record = SignalRecord(engine_id=rt.id, session_id=cfg.session_id, asset=cfg.asset, direction=direction, classification=classification, decision=decision, price=rt.last_price, call_score=result.call_score, put_score=result.put_score, signature=signature, reasons=reasons, blocks=blocks, indicators=values, order_sent=decision == "ORDER_SUBMITTED", data_timestamp=data_ts)
        async with self.manager.database.session() as db:
            await self.repo.add(db, record)
