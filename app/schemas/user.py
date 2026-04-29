from pydantic import BaseModel, Field
from app.models import UserRole

class UserOut(BaseModel):
    id: int
    username: str
    role: str
    role_display: str
    is_blocked: bool

    @classmethod
    def from_user(cls, u) -> "UserOut":
        r: UserRole = u.role if isinstance(u.role, UserRole) else UserRole(u.role)
        return cls(
            id=u.id,
            username=u.username,
            role=r.value,
            role_display=r.display_name,
            is_blocked=u.is_blocked,
        )

class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=4, max_length=256)
    role: UserRole = UserRole.SIMPLE

class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=4, max_length=256)
    role: UserRole | None = None
    is_blocked: bool | None = None
