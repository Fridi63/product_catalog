from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog

class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add(self, username: str, action: str, detail: str = "") -> None:
        row = AuditLog(username=username, action=action, detail=detail)
        self._s.add(row)
        await self._s.flush()

    async def list_recent(self, limit: int = 500) -> list[AuditLog]:
        r = await self._s.execute(
            select(AuditLog).order_by(desc(AuditLog.id)).limit(limit)
        )
        return list(r.scalars().all())
