import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime

from app.core.config import Settings
from app.core.exceptions import ExternalConnectionError
from app.core.security import ssid_fingerprint
from app.models import EngineSession
from app.repositories.database import Database
from app.repositories.engine_repository import EngineRepository
from app.schemas.connection import SessionCreate
from app.services.pocketoption_client import PocketOptionClient
from app.utils.time import utcnow


@dataclass(slots=True)
class SessionContext:
    id: str
    ssid: str
    account_mode: str
    connected: bool
    created_at: datetime
    auto_reconnect: bool


class ConnectionService:
    def __init__(self, client: PocketOptionClient, database: Database, settings: Settings):
        self.client, self.database, self.settings = client, database, settings
        self._sessions: dict[str, SessionContext] = {}
        self._lock = asyncio.Lock()
        self.repo = EngineRepository()

    def get(self, session_id: str) -> SessionContext | None:
        return self._sessions.get(session_id)

    async def create(self, request: SessionCreate) -> tuple[SessionContext, dict]:
        async with self._lock:
            if any(ssid_fingerprint(c.ssid) == ssid_fingerprint(request.ssid) for c in self._sessions.values()):
                raise ValueError("Sessão já inicializada")
            await self.client.init(request.ssid, request.persistent_connection, request.auto_reconnect, request.connect_after_init)
            if request.connect_after_init:
                stats = await self.client.connection_stats()
                connected = bool(stats.get("connected", stats.get("is_connected", True)))
            else:
                connected = False
            if request.connect_after_init and not connected:
                raise ExternalConnectionError("Não foi possível conectar à API externa")
            balance = await self.client.balance() if connected else {}
            mode = str(balance.get("account_mode", balance.get("mode", self.settings.default_account_mode))).lower()
            context = SessionContext(str(uuid.uuid4()), request.ssid, mode, connected, utcnow(), request.auto_reconnect)
            self._sessions[context.id] = context
            async with self.database.session() as db:
                await self.repo.add_session(db, EngineSession(id=context.id, ssid_hash=ssid_fingerprint(request.ssid), account_mode=mode, state="connected" if connected else "initialized"))
            return context, balance

    async def disconnect(self, session_id: str) -> None:
        context = self._sessions.get(session_id)
        if not context:
            raise KeyError(session_id)
        try:
            await self.client.disconnect()
        finally:
            context.ssid = ""
            context.connected = False
            self._sessions.pop(session_id, None)

    async def healthy(self, session_id: str) -> bool:
        context = self.get(session_id)
        if not context or not context.connected:
            return False
        try:
            stats = await self.client.connection_stats()
            context.connected = bool(stats.get("connected", stats.get("is_connected", True)))
        except ExternalConnectionError:
            context.connected = False
        return context.connected
