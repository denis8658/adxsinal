import numpy as np
import pandas as pd


def calculate_supertrend(frame: pd.DataFrame, period: int = 10, multiplier: float = 3) -> pd.DataFrame:
    high, low, close = frame.high.astype(float), frame.low.astype(float), frame.close.astype(float)
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    mid = (high + low) / 2
    upper, lower = (mid + multiplier * atr).copy(), (mid - multiplier * atr).copy()
    trend = np.ones(len(frame), dtype=int)
    line = np.full(len(frame), np.nan)
    for i in range(1, len(frame)):
        if close.iloc[i] > upper.iloc[i - 1]: trend[i] = 1
        elif close.iloc[i] < lower.iloc[i - 1]: trend[i] = -1
        else:
            trend[i] = trend[i - 1]
            if trend[i] == 1: lower.iloc[i] = max(lower.iloc[i], lower.iloc[i - 1])
            else: upper.iloc[i] = min(upper.iloc[i], upper.iloc[i - 1])
        line[i] = lower.iloc[i] if trend[i] == 1 else upper.iloc[i]
    return pd.DataFrame({"supertrend": pd.Series(line, index=frame.index).ffill().fillna(0), "trend": trend}, index=frame.index)
