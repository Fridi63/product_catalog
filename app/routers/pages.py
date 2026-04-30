from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
_TEMPL = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPL))

@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request,"index.html", {"title": "Каталог"})

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request,"login.html", {"title": "Вход"})

@router.get("/admin/users", response_class=HTMLResponse)
def users_page(request: Request):
    return templates.TemplateResponse(request,"users.html", {"title": "Пользователи"})
