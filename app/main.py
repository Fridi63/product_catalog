from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import async_session_maker, engine
from app.logging_config import setup_logging
from app.models import Base
from app.routers import api, pages
from app.seed import seed_if_empty

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as session:
        await seed_if_empty(session)
        await session.commit()
    yield


app = FastAPI(
    title="Каталог продуктов",
    description="ПО Каталог продуктов",
    lifespan=lifespan,
)

app.include_router(api.router)
app.include_router(pages.router)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
