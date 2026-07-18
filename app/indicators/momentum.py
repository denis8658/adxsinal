import pandas as pd


def calculate_momentum(frame: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    value = frame.close.astype(float).diff(period)
    return pd.DataFrame({"momentum": value, "slope": value.diff(), "cross": ((value > 0) & (value.shift() <= 0)).astype(int) - ((value < 0) & (value.shift() >= 0)).astype(int)}, index=frame.index).fillna(0)
