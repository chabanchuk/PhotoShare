from pathlib import Path
from typing import Optional, Any, Annotated

from fastapi.routing import APIRouter
from fastapi import Request, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from auth.service import auth as auth_service
from database import get_db

from frontend.model import UserFrontendModel

router = APIRouter(include_in_schema=False)

templates_path = Path(__file__).parent / 'templates'

templates = Jinja2Templates(directory=str(templates_path))


@router.get('/')
async def index(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
        access_token: Annotated[str | None, Cookie()] = None,
) -> Any:
    user = None
    if access_token:
        user_orm = await auth_service.get_access_user(access_token,
                                                      db)
        user = UserFrontendModel.from_orm(user_orm)

    return templates.TemplateResponse('index.html', {'request': request,
                                                     'user': user})


@router.get('/auth/login')
def get_login_page(request: Request,
                   next_url: Optional[str] = None) -> Any:
    return templates.TemplateResponse(
        'auth/login.html', {'request': request,
                            'user': None,
                            'error': None}
    )


@router.get('/auth/register')
async def get_register_page(request: Request,
                   next_url: Optional[str] = None) -> Any:
    return templates.TemplateResponse('auth/register.html', {'request': request})


@router.get('/htmx-test')
async def htmx_test(request: Request):
    return HTMLResponse('<h1 hx-get="/htmx-test" hx-trigger="click" hx-swap="afterend">Hello from htmx</h1>')
