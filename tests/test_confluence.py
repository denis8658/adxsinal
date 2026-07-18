from app.services.confluence_service import ConfluenceService, classify


def aligned():
    adx = {"spread": 10, "cross": 1, "expansion": 1, "slope": 1, "acceleration": 1, "persistence": 3}
    return {"adx_fast": adx, "adx_mid": adx, "adx_slow": adx, "bollinger": {"state": "EXPANSION_STRONG", "direction": "BUY_EXPANSION"}, "momentum": {"momentum": 2, "slope": 1}, "supertrend": {"trend": 1}, "structure": {"higher_low": True, "break_high": True, "lower_high": False, "break_low": False}, "zigzag": {"provisional": False}}


def test_call_confluence_scores_strongly():
    result = ConfluenceService().evaluate(aligned())
    assert result.call_score > result.put_score
    assert classify(result.call_score) in {"STRONG", "VERY_STRONG"}


def test_critical_blocks():
    result = ConfluenceService().evaluate(aligned(), stale=True, connection_healthy=False)
    assert "Dados atrasados" in result.blocks and "Conexão instável" in result.blocks
