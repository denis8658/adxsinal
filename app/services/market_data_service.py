from datetime import UTC, datetime
from typing import Any

from app.services.pocketoption_client import PocketOptionClient


class MarketDataService:
    def __init__(self, client: PocketOptionClient):
        self.client = client

    async def candles(self, asset: str, timeframe: int) -> list[dict[str, Any]]:
        response = await self.client.candles(asset, timeframe)
        items = response.get("candles", response.get("data", []))
        if not isinstance(items, list) or not items:
            raise ValueError("Formato de candles inválido")
        required = {"open", "high", "low", "close"}
        if any(not isinstance(item, dict) or not required.issubset(item) or not ({"timestamp", "time"} & item.keys()) for item in items):
            raise ValueError("Candle incompleto")
        return items

    @staticmethod
    def data_timestamp(candles: list[dict]) -> datetime:
        value = candles[-1].get("timestamp", candles[-1].get("time"))
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 10**11 else value, UTC)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return datetime.now(UTC)
