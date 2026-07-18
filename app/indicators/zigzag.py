import numpy as np
import pandas as pd


def calculate_zigzag(frame: pd.DataFrame, deviation: float = 2, depth: int = 8, backstep: int = 2) -> pd.DataFrame:
    high, low = frame.high.astype(float), frame.low.astype(float)
    pivots = np.zeros(len(frame), dtype=int)
    values = np.full(len(frame), np.nan)
    for i in range(depth, max(depth, len(frame) - backstep)):
        window_h, window_l = high.iloc[i-depth:i+1], low.iloc[i-depth:i+1]
        if high.iloc[i] >= window_h.max() and (high.iloc[i] - window_l.min()) / max(abs(window_l.min()), 1e-12) * 100 >= deviation:
            pivots[i], values[i] = 1, high.iloc[i]
        elif low.iloc[i] <= window_l.min() and (window_h.max() - low.iloc[i]) / max(abs(window_h.max()), 1e-12) * 100 >= deviation:
            pivots[i], values[i] = -1, low.iloc[i]
    provisional = np.zeros(len(frame), dtype=bool)
    if len(frame): provisional[-1] = True
    return pd.DataFrame({"pivot": pivots, "value": values, "provisional": provisional}, index=frame.index)
