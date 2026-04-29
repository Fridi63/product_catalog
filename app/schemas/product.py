from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models import User, UserRole


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    description: str
    price: Decimal = Field(ge=0)
    general_note: str = ""
    special_note: str = ""
    category_id: int = Field(ge=1)

class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=256)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    general_note: str | None = None
    special_note: str | None = None
    category_id: int | None = Field(default=None, ge=1)

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    price: Decimal
    general_note: str
    special_note: str | None
    category_id: int
    category_name: str

    @classmethod
    def from_product(cls, p, viewer: User | None) -> "ProductOut":
        hide_spec = _hide_special(viewer)
        return cls(
            id=p.id,
            name=p.name,
            description=p.description,
            price=p.price,
            general_note=p.general_note,
            special_note=None if hide_spec else p.special_note,
            category_id=p.category_id,
            category_name=p.category.name if p.category is not None else "",
        )

def _hide_special(viewer: User | None) -> bool:
    if viewer is None or viewer.is_blocked:
        return True
    r = viewer.role if isinstance(viewer.role, UserRole) else UserRole(viewer.role)
    return r == UserRole.SIMPLE
