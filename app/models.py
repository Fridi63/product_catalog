import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ADVANCED = "advanced"
    SIMPLE = "simple"

    @property
    def display_name(self) -> str:
        return {
            UserRole.SIMPLE: "Простой пользователь",
            UserRole.ADVANCED: "Продвинутый пользователь",
            UserRole.ADMIN: "Администратор",
        }[self]

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.SIMPLE,
    )
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
        passive_deletes=False,
    )

class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    general_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    special_note: Mapped[str] = mapped_column(Text, nullable=False, default="")

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[Category] = relationship(back_populates="products")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    username: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)
