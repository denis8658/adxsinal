from app.core.config import Settings
from app.services.risk_service import RiskService, RiskState


def test_order_amount_and_loss_limits():
    service = RiskService(Settings(max_order_amount=10, max_consecutive_losses=3))
    state = RiskState(consecutive_losses=3)
    blocks = service.validate(state, amount=11)
    assert "Valor excede o máximo por ordem" in blocks
    assert state.locked


def test_unlock_is_explicit():
    service = RiskService(Settings())
    state = RiskState(locked=True, reason="losses")
    service.unlock(state)
    assert not state.locked
