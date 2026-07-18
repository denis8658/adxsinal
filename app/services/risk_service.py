from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.core.config import Settings
from app.utils.time import utcnow


@dataclass
class RiskState:
    order_times: list[datetime] = field(default_factory=list)
    daily_profit_loss: float = 0
    consecutive_losses: int = 0
    last_order_at: datetime | None = None
    locked: bool = False
    reason: str | None = None


class RiskService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def validate(self, state: RiskState, *, amount: float, data_stale: bool = False, latency_ms: float = 0, connection_healthy: bool = True, active_order: bool = False, cooldown_seconds: int | None = None) -> list[str]:
        now = utcnow()
        state.order_times[:] = [x for x in state.order_times if x > now - timedelta(hours=1)]
        blocks: list[str] = []
        if state.locked: blocks.append(state.reason or "Risco bloqueado")
        if amount > self.settings.max_order_amount: blocks.append("Valor excede o máximo por ordem")
        if len(state.order_times) >= self.settings.max_orders_per_hour: blocks.append("Limite de ordens por hora")
        if state.daily_profit_loss <= -self.settings.max_daily_loss: blocks.append("Perda diária máxima")
        if state.consecutive_losses >= self.settings.max_consecutive_losses: blocks.append("Máximo de perdas consecutivas")
        wait = cooldown_seconds if cooldown_seconds is not None else self.settings.order_cooldown_seconds
        if state.last_order_at and state.last_order_at + timedelta(seconds=wait) > now: blocks.append("Cooldown ativo")
        if active_order: blocks.append("Ordem ativa para o ativo")
        if data_stale: blocks.append("Dados atrasados")
        if latency_ms > self.settings.max_external_latency_ms: blocks.append("Latência externa excessiva")
        if not connection_healthy: blocks.append("Conexão instável")
        lock_reasons = {"Perda diária máxima", "Máximo de perdas consecutivas"}
        lock = next((x for x in blocks if x in lock_reasons), None)
        if lock: state.locked, state.reason = True, lock
        return blocks

    def record_order(self, state: RiskState) -> None:
        state.last_order_at = utcnow(); state.order_times.append(state.last_order_at)

    def record_result(self, state: RiskState, profit_loss: float) -> None:
        state.daily_profit_loss += profit_loss
        state.consecutive_losses = state.consecutive_losses + 1 if profit_loss < 0 else 0

    def unlock(self, state: RiskState) -> None:
        state.locked, state.reason = False, None
