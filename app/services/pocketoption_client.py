import asyncio
import logging
from time import perf_counter
from typing import Any

import httpx

from app.core.exceptions import AmbiguousOrderError, ExternalAPIError, ExternalConnectionError

logger = logging.getLogger(__name__)


class PocketOptionClient:
    def __init__(self, base_url: str, timeout: float = 15, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout, transport=transport)
        self.last_latency_ms = 0.0

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None, retry: bool = True) -> dict[str, Any]:
        attempts = 3 if retry else 1
        for attempt in range(attempts):
            started = perf_counter()
            try:
                response = await self._client.request(method, path, json=json, params=params)
                self.last_latency_ms = (perf_counter() - started) * 1000
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ExternalAPIError("Resposta JSON inválida")
                logger.info("external_api method=%s path=%s status=%s latency_ms=%.1f", method, path, response.status_code, self.last_latency_ms)
                return data
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                self.last_latency_ms = (perf_counter() - started) * 1000
                if attempt + 1 == attempts:
                    raise ExternalConnectionError("API externa indisponível") from exc
                await asyncio.sleep(0.2 * (2**attempt))
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {429, 502, 503, 504} and attempt + 1 < attempts:
                    await asyncio.sleep(0.2 * (2**attempt)); continue
                raise ExternalAPIError(f"API externa retornou HTTP {exc.response.status_code}") from exc
            except ValueError as exc:
                raise ExternalAPIError("Resposta JSON inválida") from exc
        raise ExternalAPIError("Falha inesperada")

    async def init(self, ssid: str, persistent_connection: bool, auto_reconnect: bool, connect_after_init: bool) -> dict:
        return await self._request("POST", "/api/init", json={"ssid": ssid, "persistent_connection": persistent_connection, "auto_reconnect": auto_reconnect, "connect_after_init": connect_after_init})

    async def connect(self) -> dict: return await self._request("POST", "/api/connect", json={})
    async def disconnect(self) -> dict: return await self._request("POST", "/api/disconnect", json={}, retry=False)
    async def balance(self) -> dict: return await self._request("GET", "/api/balance")
    async def connection_stats(self) -> dict: return await self._request("GET", "/api/connection-stats")
    async def candles(self, asset: str, timeframe: int) -> dict: return await self._request("GET", "/api/candles", params={"asset": asset, "timeframe": timeframe})
    async def ticks(self, asset: str) -> dict: return await self._request("GET", f"/api/ticks/{asset}")
    async def all_ticks(self) -> dict: return await self._request("GET", "/api/ticks")
    async def assets(self) -> dict: return await self._request("GET", "/api/assets")
    async def payouts(self) -> dict: return await self._request("GET", "/api/payouts")
    async def pair_payouts(self) -> dict: return await self._request("GET", "/api/pairs/payouts")

    async def place_order(self, payload: dict) -> dict:
        try:
            return await self._request("POST", "/api/order/place", json=payload, retry=False)
        except ExternalConnectionError as exc:
            raise AmbiguousOrderError("Resultado da ordem não pôde ser confirmado") from exc
