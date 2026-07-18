import numpy as np
import pandas as pd


def calculate_adx(frame: pd.DataFrame, period: int = 14, smoothing: int | None = None) -> pd.DataFrame:
    """Wilder DMI/ADX plus the derived features consumed by the scorer."""
    if len(frame) < period + 2:
        return pd.DataFrame(index=frame.index, columns=["adx", "plus_di", "minus_di", "spread", "cross", "expansion", "slope", "acceleration", "persistence", "dominance"]).fillna(0)
    high, low, close = frame.high.astype(float), frame.low.astype(float), frame.close.astype(float)
    up, down = high.diff(), -low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=frame.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=frame.index)
    tr = pd.concat([(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    alpha = 1 / max(period, 1)
    atr = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean().replace(0, np.nan)
    plus_di = 100 * plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr
    spread = plus_di - minus_di
    dx = 100 * (spread.abs() / (plus_di + minus_di).replace(0, np.nan))
    adx_period = smoothing or period
    adx = dx.ewm(alpha=1 / max(adx_period, 1), adjust=False, min_periods=adx_period).mean()
    cross = pd.Series(np.where((spread > 0) & (spread.shift() <= 0), 1, np.where((spread < 0) & (spread.shift() >= 0), -1, 0)), index=frame.index)
    persistence = spread.gt(0).rolling(3).sum() - spread.lt(0).rolling(3).sum()
    result = pd.DataFrame({
        "adx": adx, "plus_di": plus_di, "minus_di": minus_di, "spread": spread,
        "cross": cross, "expansion": spread.abs().diff(), "slope": adx.diff(),
        "acceleration": adx.diff().diff(), "persistence": persistence,
        "dominance": np.sign(spread),
    })
    return result.replace([np.inf, -np.inf], np.nan).fillna(0.0)
