from dataclasses import asdict

from app.services.engine_manager import EngineRuntime


class EngineService:
    @staticmethod
    def status(runtime: EngineRuntime) -> dict:
        return runtime.status_payload()

    @staticmethod
    def config(runtime: EngineRuntime) -> dict:
        return asdict(runtime.config)
