class TradingEngineError(Exception):
    code = "TRADING_ENGINE_ERROR"


class ExternalAPIError(TradingEngineError):
    code = "POCKETOPTION_API_ERROR"


class ExternalConnectionError(ExternalAPIError):
    code = "POCKETOPTION_CONNECTION_FAILED"


class AmbiguousOrderError(ExternalAPIError):
    code = "AMBIGUOUS_ORDER_RESPONSE"


class InvalidStateTransition(TradingEngineError):
    code = "INVALID_STATE_TRANSITION"


class RiskLockedError(TradingEngineError):
    code = "RISK_LOCKED"
