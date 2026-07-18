from fastapi import Request

from app.repositories.database import Database
from app.services.connection_service import ConnectionService
from app.services.engine_manager import EngineManager


def connections(request: Request) -> ConnectionService: return request.app.state.connections
def engines(request: Request) -> EngineManager: return request.app.state.engines
def database(request: Request) -> Database: return request.app.state.database
