import json

import httpx
import pytest

from app.core.exceptions import AmbiguousOrderError, ExternalConnectionError
from app.services.pocketoption_client import PocketOptionClient


@pytest.mark.asyncio
async def test_candles_use_post_body_and_normalize_list_response():
    async def handler(request: httpx.Request):
        assert request.method == "POST"
        assert request.url.path == "/api/candles"
        assert json.loads(request.content) == {"asset": "EURGBP_otc", "timeframe": 5, "count": 100}
        return httpx.Response(200, json=[{"timestamp": 1_700_000_000, "open": 1, "high": 2, "low": .5, "close": 1.5}])

    client = PocketOptionClient("https://example.test", transport=httpx.MockTransport(handler))
    response = await client.candles("EURGBP_otc", 5)

    assert response["candles"][0]["close"] == 1.5
    await client.close()


@pytest.mark.asyncio
async def test_ambiguous_order_is_not_retried():
    calls = 0
    async def handler(request):
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout", request=request)
    client = PocketOptionClient("https://example.test", transport=httpx.MockTransport(handler))
    with pytest.raises(AmbiguousOrderError):
        await client.place_order({"asset": "EURUSD_otc", "direction": "CALL", "amount": 1, "duration_seconds": 30})
    assert calls == 1
    await client.close()


@pytest.mark.asyncio
async def test_get_retries_transient_failures():
    calls = 0
    async def handler(request):
        nonlocal calls
        calls += 1
        if calls < 3: raise httpx.ConnectError("down", request=request)
        return httpx.Response(200, json={"connected": True})
    client = PocketOptionClient("https://example.test", transport=httpx.MockTransport(handler))
    assert (await client.connection_stats())["connected"]
    assert calls == 3
    await client.close()
