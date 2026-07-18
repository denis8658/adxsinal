import numpy as np
import pandas as pd


def calculate_bollinger(frame: pd.DataFrame, period: int = 20, std_multiplier: float = 2) -> pd.DataFrame:
    close = frame.close.astype(float)
    middle = close.rolling(period).mean()
    std = close.rolling(period).std(ddof=0)
    upper, lower = middle + std_multiplier * std, middle - std_multiplier * std
    width = (upper - lower) / middle.replace(0, np.nan)
    growth = width.diff()
    accel = growth.diff()
    state = np.select(
        [(growth < 0), (growth > 0) & (accel > 0), (growth > 0) & (accel <= 0)],
        ["CONTRACTION", "EXPANSION_STRONG", "EXPANSION_CONFIRMED"], default="COMPRESSION")
    direction = np.select(
        [(growth > 0) & (close > middle) & (upper.diff() > 0) & (middle.diff() > 0),
         (growth > 0) & (close < middle) & (lower.diff() < 0) & (middle.diff() < 0)],
        ["BUY_EXPANSION", "SELL_EXPANSION"], default="NEUTRAL_EXPANSION")
    return pd.DataFrame({"middle": middle, "upper": upper, "lower": lower, "width": width, "width_growth": growth, "width_acceleration": accel, "state": state, "direction": direction}, index=frame.index).replace([np.inf, -np.inf], np.nan).fillna(0)
