import hashlib
from datetime import datetime

from app.services.confluence_service import ConfluenceResult, classify


class SignalService:
    @staticmethod
    def choose(result: ConfluenceResult, minimum: int, difference: int) -> tuple[str | None, int, str]:
        if abs(result.call_score - result.put_score) < difference:
            return None, max(result.call_score, result.put_score), "NO_SIGNAL"
        direction = "CALL" if result.call_score > result.put_score else "PUT"
        score = max(result.call_score, result.put_score)
        if score < minimum:
            return None, score, classify(score)
        return direction, score, classify(score)

    @staticmethod
    def signature(asset: str, direction: str, timeframe: int, candle_timestamp: datetime, cross_timestamp: str, pivot_timestamp: str) -> str:
        rounded = int(candle_timestamp.timestamp()) // max(timeframe, 1) * max(timeframe, 1)
        raw = f"{asset}|{direction}|{timeframe}|{rounded}|{cross_timestamp}|{pivot_timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()
