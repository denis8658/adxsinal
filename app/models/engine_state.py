from enum import StrEnum

from app.core.exceptions import InvalidStateTransition


class EngineStatus(StrEnum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    CONNECTION_LOST = "CONNECTION_LOST"
    RISK_LOCKED = "RISK_LOCKED"
    ERROR = "ERROR"


TRANSITIONS = {
    EngineStatus.STOPPED: {EngineStatus.STARTING},
    EngineStatus.STARTING: {EngineStatus.RUNNING, EngineStatus.ERROR, EngineStatus.STOPPING},
    EngineStatus.RUNNING: {EngineStatus.PAUSED, EngineStatus.STOPPING, EngineStatus.CONNECTION_LOST, EngineStatus.RISK_LOCKED, EngineStatus.ERROR},
    EngineStatus.PAUSED: {EngineStatus.RUNNING, EngineStatus.STOPPING, EngineStatus.CONNECTION_LOST, EngineStatus.RISK_LOCKED},
    EngineStatus.CONNECTION_LOST: {EngineStatus.RUNNING, EngineStatus.STOPPING, EngineStatus.ERROR},
    EngineStatus.RISK_LOCKED: {EngineStatus.STOPPING, EngineStatus.RUNNING},
    EngineStatus.ERROR: {EngineStatus.STOPPING, EngineStatus.STOPPED},
    EngineStatus.STOPPING: {EngineStatus.STOPPED},
}


def ensure_transition(current: EngineStatus, target: EngineStatus, *, risk_unlocked: bool = False) -> None:
    if target not in TRANSITIONS[current] or (current == EngineStatus.RISK_LOCKED and target == EngineStatus.RUNNING and not risk_unlocked):
        raise InvalidStateTransition(f"Transição inválida: {current} -> {target}")
