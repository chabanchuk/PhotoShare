import jose
from jose import jwt
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import RedirectResponse

from middlewares.registrator import register_modder
from frontend.routes import templates

from settings import settings


@register_modder('get_my_profile')
async def html_get_my_profile(request: Request,
                              response: Response,
                              data: dict) -> Any:
    """HTMX transformer for get_my_profile response

            Args:
                response (Response): response object to handle
                data (dict): mapped response data

            Returns:
                HTML data for htmx
    """
    print("Response handler for get_my_profile", data)

    return response


@register_modder('auth_login')
async def html_auth_login(request: Request,
                          response: Response,
                          data: dict) -> Any:
    """HTMX transformer for auth_login response

            Args:
                response (Response): response object to handle
                data (dict): mapped response data

            Returns:
                HTML data for htmx
    """
    status_code = response.status_code
    if status_code >= 400:
        error_message = data.get('detail').get('msg')
        return templates.TemplateResponse(
            'auth/login.html', {'request': request,
                                'error': error_message}
        )
    access_token = data.get('access_token')
    try:
        access_payload = jwt.decode(token=access_token,
                                    key=settings.secret_256,
                                    algorithms=[settings.access_algorithm])
    except jose.exceptions.JWTError:
        return templates.TemplateResponse(
            'auth/login.html', {'request': request,
                                'error': 'Invalid credentials'}
        )

    refresh_token = data.get('refresh_token')
    try:
        refresh_payload = jwt.decode(token=refresh_token,
                                    key=settings.secret_512,
                                    algorithms=[settings.refresh_algorithm])
    except jose.exceptions.JWTError:
        return templates.TemplateResponse(
            'auth/login.html', {'request': request,
                                'error': 'Invalid credentials',
                                'user': None}
        )

    response = RedirectResponse('/',
                                status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key='access_token',
                        value=access_token,
                        httponly=True,
                        expires=access_payload.get('exp'))
    response.set_cookie(key='refresh_token',
                        value=refresh_token,
                        httponly=True,
                        expires=refresh_payload.get('exp'))
    return response


@register_modder('auth_logout')
async def html_auth_logout(request: Request,
                           response: Response,
                           data: dict) -> Any:
    """HTMX transformer for auth_logout response

            Args:
                request (Request): request object to handle
                response (Response): response object to handle
                data (dict): mapped response data

            Returns:
                HTML data for htmx
    """
    response = RedirectResponse('/',
                                status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response


@register_modder('get_photos')
async def html_get_photos(request: Request,
                          response: Response,
                          data: dict) -> Any:
    """HTMX transformer for get_photos response

            Args:
                response (Response): response object to handle
                data (dict): mapped response data

            Returns:
                HTML data for htmx
    """
    return response