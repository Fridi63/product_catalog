from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_current_user, get_db, get_optional_user, require_roles
from app.logging_config import get_logger
from app.models import User, UserRole
from app.repositories import AuditRepository, CategoryRepository, ProductRepository, UserRepository
from app.schemas.auth import LoginRequest
from app.schemas.category import CategoryIn, CategoryOut
from app.schemas.product import ProductIn, ProductOut, ProductUpdate
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.security import create_access_token, get_password_hash, verify_password
from app.services.nbrb import NbrbError, convert_byn_to_usd

log = get_logger("app.api")
router = APIRouter(prefix="/api")

SIMPLE_ADVANCED_ADMIN = (UserRole.SIMPLE, UserRole.ADVANCED, UserRole.ADMIN)
ADVANCED_ADMIN = (UserRole.ADVANCED, UserRole.ADMIN)
ADMIN = (UserRole.ADMIN,)

@router.post("/auth/login")
async def login(data: LoginRequest, session: AsyncSession = Depends(get_db)):
    urepo = UserRepository(session)
    user = await urepo.get_by_username(data.username)
    if user is None or not verify_password(data.password, user.password):
        log.warning("Неудачный вход: %s", data.username)
        raise HTTPException(status_code=400, detail="Неверные учётные данные")
    if user.is_blocked:
        log.warning("Попытка входа заблокированного: %s", data.username)
        raise HTTPException(status_code=403, detail="Пользователь заблокирован")
    a = AuditRepository(session)
    await a.add(user.username, "LOGIN", f"user_id={user.id}")
    return {
        "access_token": create_access_token(sub=user.username, user_id=user.id),
        "token_type": "bearer",
    }

@router.get("/auth/me", response_model=UserOut)
async def me(u: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_user(u)

@router.get("/fx/byn-to-usd")
async def byn_to_usd(
    amount_byn: Decimal = Query(..., ge=0),
    on: date | None = Query(default=None, description="Дата курса; по умолчанию сегодня"),
):
    d = on or date.today()
    try:
        r = await convert_byn_to_usd(amount_byn, d)
    except NbrbError as e:
        log.info("NBRB: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    return r

@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    session: AsyncSession = Depends(get_db),
    _: User | None = Depends(get_optional_user),
):
    crepo = CategoryRepository(session)
    cats = await crepo.list_all()
    return [
        CategoryOut(id=c.id, name=c.name, product_count=len(c.products or [])) for c in cats
    ]

@router.post("/categories", response_model=CategoryOut)
async def create_category(
    data: CategoryIn,
    user: User = Depends(require_roles(*ADVANCED_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    cr = CategoryRepository(session)
    if await cr.get_by_name(data.name):
        raise HTTPException(status_code=400, detail="Категория с таким именем есть")
    c = await cr.create(data.name)
    await AuditRepository(session).add(user.username, "CATEGORY_CREATE", f"id={c.id} {c.name}")
    log.info("Категория создана: %s", c.id)
    return CategoryOut(id=c.id, name=c.name, product_count=0)

@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    data: CategoryIn,
    user: User = Depends(require_roles(*ADVANCED_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    cr = CategoryRepository(session)
    c = await cr.get(category_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    other = await cr.get_by_name(data.name)
    if other is not None and other.id != c.id:
        raise HTTPException(status_code=400, detail="Имя занято")
    c.name = data.name.strip()
    await cr.save(c)
    await AuditRepository(session).add(user.username, "CATEGORY_UPDATE", f"id={c.id} {c.name}")
    n = await cr.count_products(c.id)
    return CategoryOut(id=c.id, name=c.name, product_count=n)

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    user: User = Depends(require_roles(*ADVANCED_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    cr = CategoryRepository(session)
    c = await cr.get(category_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    name = c.name
    n = await cr.count_products(c.id)
    await cr.delete(c)
    await AuditRepository(session).add(
        user.username, "CATEGORY_DELETE", f"id={category_id} {name} products={n}"
    )
    return None

@router.get("/products", response_model=list[ProductOut])
async def list_products(
    session: AsyncSession = Depends(get_db),
    q: str | None = None,
    category_id: int | None = None,
    viewer: User | None = Depends(get_optional_user),
):
    pr = ProductRepository(session)
    products = await pr.list_filtered(search=q, category_id=category_id)
    return [ProductOut.from_product(p, viewer) for p in products]

@router.post("/products", response_model=ProductOut)
async def create_product(
    data: ProductIn,
    user: User = Depends(require_roles(*SIMPLE_ADVANCED_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    cr = CategoryRepository(session)
    cat = await cr.get(data.category_id)
    if cat is None:
        raise HTTPException(status_code=400, detail="Категория не существует")
    role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    spec = data.special_note
    if role == UserRole.SIMPLE:
        spec = ""
    pr = ProductRepository(session)
    p = await pr.create(
        name=data.name,
        description=data.description,
        price=data.price,
        general_note=data.general_note,
        special_note=spec,
        category_id=data.category_id,
    )
    p = await pr.get(p.id)  # reload with category
    await AuditRepository(session).add(
        user.username, "PRODUCT_CREATE", f"id={p.id} {p.name}"
    )
    return ProductOut.from_product(p, user)

@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    session: AsyncSession = Depends(get_db),
    viewer: User | None = Depends(get_optional_user),
):
    pr = ProductRepository(session)
    p = await pr.get(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return ProductOut.from_product(p, viewer)


@router.patch("/products/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    user: User = Depends(require_roles(*SIMPLE_ADVANCED_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    pr = ProductRepository(session)
    p = await pr.get(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    role = user.role if isinstance(user.role, UserRole) else UserRole(user.role)
    u = data.model_dump(exclude_unset=True)
    if u.get("category_id") is not None:
        cr = CategoryRepository(session)
        c = await cr.get(int(u["category_id"]))
        if c is None:
            raise HTTPException(status_code=400, detail="Категория не существует")
    if "special_note" in u and role == UserRole.SIMPLE:
        u.pop("special_note")
    for k, v in u.items():
        setattr(p, k, v)
    await pr.save(p)
    p = await pr.get(product_id)
    await AuditRepository(session).add(user.username, "PRODUCT_UPDATE", f"id={p.id}")
    return ProductOut.from_product(p, user)

@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    user: User = Depends(require_roles(*ADVANCED_ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    pr = ProductRepository(session)
    p = await pr.get(product_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    nm = p.name
    await pr.delete(p)
    await AuditRepository(session).add(
        user.username, "PRODUCT_DELETE", f"id={product_id} {nm}"
    )
    return None

@router.get("/users", response_model=list[UserOut])
async def list_users(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(*ADMIN)),
):
    rows = await UserRepository(session).list_all()
    return [UserOut.from_user(u) for u in rows]

@router.post("/users", response_model=UserOut)
async def create_user(
    data: UserCreate,
    user: User = Depends(require_roles(*ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    urep = UserRepository(session)
    if await urep.get_by_username(data.username):
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    u = await urep.create(
        data.username, get_password_hash(data.password), data.role
    )
    log.info("Создан пользователь %s админом %s", u.id, user.username)
    await AuditRepository(session).add(
        user.username, "USER_CREATE", f"id={u.id} login={u.username} role={u.role.value}"
    )
    return UserOut.from_user(u)

@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    data: UserUpdate,
    admin: User = Depends(require_roles(*ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    urep = UserRepository(session)
    u = await urep.get_by_id(user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    udata = data.model_dump(exclude_unset=True)
    if "password" in udata and udata["password"]:
        u.password = get_password_hash(str(udata["password"]))
    if "role" in udata and udata["role"] is not None:
        u.role = udata["role"]
    if "is_blocked" in udata and udata["is_blocked"] is not None:
        u.is_blocked = bool(udata["is_blocked"])
    await urep.save(u)
    await AuditRepository(session).add(
        admin.username, "USER_UPDATE", f"id={u.id} login={u.username}"
    )
    return UserOut.from_user(u)

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    admin: User = Depends(require_roles(*ADMIN)),
    session: AsyncSession = Depends(get_db),
):
    urep = UserRepository(session)
    u = await urep.get_by_id(user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if u.id == admin.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить свою учётку")
    login = u.username
    await urep.delete(u)
    await AuditRepository(session).add(
        admin.username, "USER_DELETE", f"id={user_id} {login}"
    )
    return None

@router.get("/audit-logs", response_model=list[dict])
async def audit_logs(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(*ADMIN)),
):
    rows = await AuditRepository(session).list_recent(400)
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "username": r.username,
            "action": r.action,
            "detail": r.detail,
        }
        for r in rows
    ]
