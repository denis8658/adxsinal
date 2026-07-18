import uuid
from datetime import timedelta

from app.core.exceptions import AmbiguousOrderError
from app.models import OrderRecord
from app.repositories.database import Database
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderStatus
from app.services.pocketoption_client import PocketOptionClient
from app.utils.time import utcnow


class OrderService:
    def __init__(self, client: PocketOptionClient, database: Database):
        self.client, self.database, self.repo = client, database, OrderRepository()

    async def place(self, engine_id: str, asset: str, direction: str, amount: float, duration: int, idempotency_key: str) -> OrderRecord:
        record = OrderRecord(id=str(uuid.uuid4()), engine_id=engine_id, asset=asset, direction=direction, amount=amount, status=OrderStatus.SUBMITTING, idempotency_key=idempotency_key, expires_at=utcnow() + timedelta(seconds=duration))
        async with self.database.session() as db:
            if await self.repo.signature_used(db, idempotency_key):
                record.status = OrderStatus.CANCELLED; record.error = "Assinatura já utilizada"; return record
            await self.repo.add(db, record)
            try:
                response = await self.client.place_order({"asset": asset, "direction": direction, "amount": amount, "duration_seconds": duration})
                record.external_id = str(response.get("order_id", response.get("id", ""))) or None
                record.status = OrderStatus.ACCEPTED if response.get("success", True) else OrderStatus.REJECTED
            except AmbiguousOrderError:
                record.status = OrderStatus.UNKNOWN; record.error = "Resultado ambíguo; requisição não repetida"
            except Exception as exc:
                record.status = OrderStatus.FAILED; record.error = type(exc).__name__
            await db.commit()
        return record
