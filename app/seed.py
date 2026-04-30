from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Product, User, UserRole
from app.security import get_password_hash


async def seed_if_empty(session: AsyncSession) -> None:
    user_exists = await session.scalar(select(User.id).limit(1))
    if user_exists is None:
        session.add_all(
            [
                User(
                    username="admin",
                    password=get_password_hash("qwerty123"),
                    role=UserRole.ADMIN,
                ),
                User(
                    username="advanced",
                    password=get_password_hash("qwerty123"),
                    role=UserRole.ADVANCED,
                ),
                User(
                    username="simple",
                    password=get_password_hash("qwerty123"),
                    role=UserRole.SIMPLE,
                ),
            ]
        )

    category_exists = await session.scalar(select(Category.id).limit(1))
    if category_exists is None:
        food = Category(name="Еда")
        sweets = Category(name="Вкусности")
        water = Category(name="Вода")
        session.add_all([food, sweets, water])
        await session.flush()

    product_exists = await session.scalar(select(Product.id).limit(1))
    if product_exists is None:
        categories = await session.execute(select(Category))
        categories_by_name = {c.name: c.id for c in categories.scalars().all()}
        session.add_all(
            [
                Product(
                    name="Селедка",
                    description="Селедка соленая",
                    price=Decimal("10.0000"),
                    general_note="Акция",
                    special_note="Пересоленая",
                    category_id=categories_by_name["Еда"],
                ),
                Product(
                    name="Тушенка",
                    description="Тушенка говяжья",
                    price=Decimal("20.0000"),
                    general_note="Вкусная",
                    special_note="Жилы",
                    category_id=categories_by_name["Еда"],
                ),
                Product(
                    name="Сгущенка",
                    description="В банках",
                    price=Decimal("30.0000"),
                    general_note="С ключом",
                    special_note="Вкусная",
                    category_id=categories_by_name["Вкусности"],
                ),
                Product(
                    name="Квас",
                    description="В бутылках",
                    price=Decimal("15.0000"),
                    general_note="Вятский",
                    special_note="Теплый",
                    category_id=categories_by_name["Вода"],
                ),
            ]
        )
