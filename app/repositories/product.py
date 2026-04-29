from decimal import Decimal
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import Product

class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get(self, product_id: int) -> Product | None:
        r = await self._s.execute(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id)
        )
        return r.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        search: str | None,
        category_id: int | None,
    ) -> list[Product]:
        q = select(Product).options(selectinload(Product.category))
        if category_id is not None:
            q = q.where(Product.category_id == category_id)
        if search and search.strip():
            t = f"%{search.strip()}%"
            q = q.where(
                or_(
                    Product.name.ilike(t),
                    Product.description.ilike(t),
                    Product.general_note.ilike(t),
                )
            )
        q = q.order_by(Product.name)
        r = await self._s.execute(q)
        return list(r.scalars().all())

    async def create(
        self,
        *,
        name: str,
        description: str,
        price: Decimal,
        general_note: str,
        special_note: str,
        category_id: int,
    ) -> Product:
        p = Product(
            name=name.strip(),
            description=description,
            price=price,
            general_note=general_note,
            special_note=special_note,
            category_id=category_id,
        )
        self._s.add(p)
        await self._s.flush()
        return p

    async def save(self, p: Product) -> None:
        self._s.add(p)
        await self._s.flush()

    async def delete(self, p: Product) -> None:
        await self._s.delete(p)
