from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from app.models import Category, Product

class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, category_id: int) -> Category | None:
        return await self._s.get(Category, category_id)

    async def get_by_name(self, name: str) -> Category | None:
        r = await self._s.execute(select(Category).where(Category.name == name).limit(1))
        return r.scalar_one_or_none()

    async def list_all(self) -> list[Category]:
        r = await self._s.execute(
            select(Category).order_by(Category.name).options(selectinload(Category.products))
        )
        return list(r.scalars().unique().all())

    async def create(self, name: str) -> Category:
        c = Category(name=name.strip())
        self._s.add(c)
        await self._s.flush()
        return c

    async def save(self, c: Category) -> None:
        self._s.add(c)
        await self._s.flush()

    async def delete(self, c: Category) -> None:
        await self._s.execute(delete(Product).where(Product.category_id == c.id))
        await self._s.delete(c)

    async def count_products(self, category_id: int) -> int:
        q = await self._s.execute(
            select(func.count()).select_from(Product).where(Product.category_id == category_id)
        )
        return int(q.scalar_one())
