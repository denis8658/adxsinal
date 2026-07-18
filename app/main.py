import logging
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import account, connection, engine, health, signals
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.repositories.database import Database
from app.services.connection_service import ConnectionService
from app.services.engine_manager import EngineManager
from app.services.pocketoption_client import PocketOptionClient


class SecurityLimitsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app); self.settings = settings; self.requests = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.method in {"POST", "PATCH", "PUT"}:
            try:
                length = int(request.headers.get("content-length", "0") or 0)
            except ValueError:
                return JSONResponse({"error": "Content-Length inválido", "status": 400}, status_code=400)
            if length > self.settings.max_body_bytes: return JSONResponse({"detail": {"code": "BODY_TOO_LARGE", "message": "Corpo da requisição excede o limite."}}, status_code=413)
        if request.url.path in {"/api/v1/connection/session", "/api/v1/engine/start", "/api/v1/engine/unlock-risk"}:
            key = request.client.host if request.client else "unknown"; now = monotonic(); queue = self.requests[key]
            while queue and queue[0] < now - self.settings.sensitive_rate_window_seconds: queue.popleft()
            if len(queue) >= self.settings.sensitive_rate_limit: return JSONResponse({"detail": {"code": "RATE_LIMITED", "message": "Muitas requisições."}}, status_code=429)
            queue.append(now)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if request.headers.get("x-forwarded-proto", request.url.scheme) == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def create_app(settings: Settings | None = None, *, client: PocketOptionClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        database = Database(settings)
        if settings.auto_create_schema:
            await database.create_all()
        external = client or PocketOptionClient(settings.pocketoption_base_url, settings.http_timeout_seconds)
        connections_service = ConnectionService(external, database, settings)
        manager = EngineManager(connections_service, external, database, settings)
        app.state.database, app.state.client, app.state.connections, app.state.engines = database, external, connections_service, manager
        yield
        await manager.shutdown(); await external.close(); await database.close()

    app = FastAPI(title="PocketOption Auto Trading Engine API", version="1.0.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def safe_validation_error(request: Request, exc: RequestValidationError):
        errors = []
        for item in exc.errors():
            clean = dict(item)
            if "ssid" in clean.get("loc", ()) or "x-engine-key" in clean.get("loc", ()):
                clean["input"] = "[REDACTED]"
            errors.append(clean)
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception):
        logging.getLogger(__name__).error("unhandled_error path=%s type=%s", request.url.path, type(exc).__name__, exc_info=settings.debug)
        return JSONResponse(status_code=500, content={"error": "Erro interno", "status": 500})
    app.add_middleware(SecurityLimitsMiddleware, settings=settings)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-Engine-Key"], allow_credentials=False)
    for router in (connection.router, engine.router, account.router, signals.router, health.router): app.include_router(router)
    return app


app = create_app()
