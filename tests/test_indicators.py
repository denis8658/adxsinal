import numpy as np
import pandas as pd

from app.indicators.adx import calculate_adx
from app.indicators.bollinger import calculate_bollinger


def candles(size=100):
    close = np.linspace(1, 2, size) + np.sin(np.arange(size) / 4) * .02
    return pd.DataFrame({"open": close-.005, "high": close+.02, "low": close-.02, "close": close})


def test_three_adx_are_finite():
    frame = candles()
    for period, smoothing in [(5, 1), (10, 2), (14, 14)]:
        result = calculate_adx(frame, period, smoothing)
        assert {"adx", "plus_di", "minus_di", "cross", "expansion", "acceleration"} <= set(result)
        assert np.isfinite(result.to_numpy()).all()


def test_bollinger_width_formula():
    result = calculate_bollinger(candles()).iloc[-1]
    assert result.width == pytest.approx((result.upper-result.lower)/result.middle)


import pytest
