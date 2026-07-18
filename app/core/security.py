import hashlib
import secrets

from fastapi import Header, HTTPException, Request, status

from app.core.config import Settings


def verify_engine_key(candidate: str, expected: str) -> bool:
    return secrets.compare_digest(candidate.encode(), expected.encode())


def ssid_fingerprint(ssid: str) -> str:
    return hashlib.sha256(ssid.encode()).hexdigest()


async def require_engine_key(
    request: Request,
    x_engine_key: str | None = Header(default=None, alias="X-Engine-Key"),
) -> None:
    settings: Settings = request.app.state.settings
    if x_engine_key is None or not verify_engine_key(x_engine_key, settings.engine_master_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_ENGINE_KEY", "message": "Chave do motor inválida."})
