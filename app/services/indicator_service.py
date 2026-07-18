from typing import Any

import pandas as pd

from app.indicators import calculate_adx, calculate_bollinger, calculate_momentum, calculate_supertrend, calculate_zigzag
from app.indicators.market_structure import detect_market_structure


class IndicatorService:
    def calculate(self, candles: list[dict[str, Any]]) -> dict[str, Any]:
        frame = pd.DataFrame(candles).rename(columns={"timestamp": "time"})
        required = {"open", "high", "low", "close"}
        if len(frame) < 30 or not required.issubset(frame.columns):
            raise ValueError("Candles insuficientes ou inválidos")
        if frame[list(required)].isna().any().any():
            raise ValueError("Candles contêm valores ausentes")
        adx_fast = calculate_adx(frame, 5, 1)
        adx_mid = calculate_adx(frame, 10, 2)
        adx_slow = calculate_adx(frame, 14, 14)
        bollinger = calculate_bollinger(frame)
        momentum = calculate_momentum(frame)
        zigzag = calculate_zigzag(frame)
        supertrend = calculate_supertrend(frame)
        def last(table: pd.DataFrame) -> dict:
            return {k: (v.item() if hasattr(v, "item") else v) for k, v in table.iloc[-1].to_dict().items()}
        return {"adx_fast": last(adx_fast), "adx_mid": last(adx_mid), "adx_slow": last(adx_slow), "bollinger": last(bollinger), "momentum": last(momentum), "zigzag": last(zigzag), "structure": detect_market_structure(frame, zigzag), "supertrend": last(supertrend)}
