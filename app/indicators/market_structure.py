import pandas as pd


def detect_market_structure(frame: pd.DataFrame, zigzag: pd.DataFrame) -> dict:
    points = zigzag[zigzag["pivot"] != 0]
    highs = points[points["pivot"] == 1]["value"].dropna()
    lows = points[points["pivot"] == -1]["value"].dropna()
    close = float(frame.close.iloc[-1])
    last_high = float(highs.iloc[-1]) if len(highs) else None
    last_low = float(lows.iloc[-1]) if len(lows) else None
    return {
        "higher_high": bool(len(highs) >= 2 and highs.iloc[-1] > highs.iloc[-2]),
        "lower_high": bool(len(highs) >= 2 and highs.iloc[-1] < highs.iloc[-2]),
        "higher_low": bool(len(lows) >= 2 and lows.iloc[-1] > lows.iloc[-2]),
        "lower_low": bool(len(lows) >= 2 and lows.iloc[-1] < lows.iloc[-2]),
        "break_high": bool(last_high is not None and close > last_high),
        "break_low": bool(last_low is not None and close < last_low),
        "last_pivot_timestamp": str(points.index[-1]) if len(points) else "none",
    }
