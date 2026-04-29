from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User

class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._s.get(User, user_id)

    async def get_by_username(self, username: str) -> User | None:
        r = await self._s.execute(select(User).where(User.username == username).limit(1))
        return r.scalar_one_or_none()

    async def list_all(self) -> list[User]:
        r = await self._s.execute(select(User).order_by(User.username))
        return list(r.scalars().all())

    async def create(self, username: str, password_hash: str, role) -> User:
        u = User(username=username, password=password_hash, role=role)
        self._s.add(u)
        await self._s.flush()
        return u

    async def save(self, user: User) -> None:
        self._s.add(user)
        await self._s.flush()

    async def delete(self, user: User) -> None:
        await self._s.delete(user)
