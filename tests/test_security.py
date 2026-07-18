from app.core.security import verify_engine_key
from app.core.config import Settings
from app.utils.masks import mask_secret, mask_sensitive_text


def test_key_validation_and_masking():
    assert verify_engine_key("abc", "abc")
    assert not verify_engine_key("abc", "abd")
    secret = '42["auth",{"session":"top-secret"}]'
    assert secret not in mask_sensitive_text(secret)
    assert "..." in mask_secret(secret)


def test_railway_postgres_url_is_asyncpg_compatible():
    settings = Settings(database_url="postgresql://user:pass@host/db?sslmode=require")
    assert settings.normalized_database_url == "postgresql+asyncpg://user:pass@host/db?ssl=require"


def test_security_headers(client):
    response = client.get("/live", headers={"X-Forwarded-Proto": "https"})
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "max-age=" in response.headers["strict-transport-security"]
