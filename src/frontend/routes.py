from pathlib import Path
from typing import Optional, Any

from fastapi.routing import APIRouter
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(include_in_schema=False)

templates_path = Path(__file__).parent / 'templates'

templates = Jinja2Templates(directory=str(templates_path))


@router.get('/')
def index(request: Request) -> Any:
    return templates.TemplateResponse('index.html', {'request': request})


@router.get('/auth/login')
def get_login_page(request: Request,
                   next_url: Optional[str] = None) -> Any:
    return templates.TemplateResponse('auth/login.html', {'request': request})


@router.get('/auth/register')
async def get_register_page(request: Request,
                   next_url: Optional[str] = None) -> Any:
    return templates.TemplateResponse('auth/register.html', {'request': request})


@router.get('/htmx-test')
async def htmx_test(request: Request):
    return HTMLResponse('<h1 hx-get="/htmx-test" hx-trigger="click" hx-swap="afterend">Hello from htmx</h1>')
