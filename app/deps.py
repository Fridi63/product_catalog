from collections.abc import Callable, Coroutine
from typing import Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db as _get_db
from app.models import User, UserRole
from app.repositories import UserRepository
from app.security import decode_token

_bearer = HTTPBearer(auto_error=False)
get_db = _get_db

async def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)

async def get_optional_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_db),
) -> User | None:
    if cred is None or cred.scheme.lower() != "bearer":
        return None
    payload = decode_token(cred.credentials)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    u = await UserRepository(session).get_by_username(str(sub))
    if u is None or u.is_blocked:
        return None
    return u

async def get_current_user(
    user: User | None = Depends(get_optional_user),
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется вход")
    return user

def require_roles(*allowed: UserRole) -> Callable[..., Coroutine[Any, Any, User]]:
    async def dep(u: User = Depends(get_current_user)) -> User:
        r: UserRole = u.role if isinstance(u.role, UserRole) else UserRole(u.role)
        if r not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return u

    return dep
