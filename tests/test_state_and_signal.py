from datetime import UTC, datetime

import pytest

from app.core.exceptions import InvalidStateTransition
from app.models.engine_state import EngineStatus, ensure_transition
from app.services.signal_service import SignalService


def test_invalid_state_transition():
    with pytest.raises(InvalidStateTransition): ensure_transition(EngineStatus.STOPPED, EngineStatus.PAUSED)


def test_signal_signature_is_deterministic_and_sensitive_to_direction():
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    first = SignalService.signature("EURUSD_otc", "CALL", 5, timestamp, "cross", "pivot")
    assert first == SignalService.signature("EURUSD_otc", "CALL", 5, timestamp, "cross", "pivot")
    assert first != SignalService.signature("EURUSD_otc", "PUT", 5, timestamp, "cross", "pivot")
