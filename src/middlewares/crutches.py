"""
Module provides necessary functions to compensate absence of JS skill
Because we do want to have a nice frontend without heavy React or other
js based framework with all these webpacks, nmps and so on
"""
import copy
import json
import re
import urllib.parse

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from middlewares import response_handlers
from middlewares.registrator import RESPONSE_MODDERS


async def cookie_to_header_jwt(request: Request,
                               call_next):
    token = request.cookies.get('access_token')
    if request.scope.get('path') == '/auth/refresh':
        token = request.cookies.get('refresh_token')
    if token:
        headers = dict(request.scope['headers'])
        headers[b'authorization'] = f'bearer {token}'.encode()
        request.scope['headers'] = [(k, v) for k, v in headers.items()]
    response = await call_next(request)
    return response


async def modify_json_response(request: Request,
                               call_next):

    browser_regexp = (r"Mozilla|Chrome|Chromium|Apple|WebKit|" +
                      r"Edge|IE|MSIE|Firefox|Gecko")
    docs_redoc_regexp = (r"/docs$|/docs#|/docs/|/redoc$|/redoc#|/redoc/"
                         + r"|/openapi.json$|/static/|/favicon.ico$")

    referer = request.headers.get('referer')
    referer = referer if referer else ""

    swagger_static_match = any(
        (re.search(
            pattern=docs_redoc_regexp,
            string=str(request.url),
            flags=re.I
        ),
         re.search(
             pattern=docs_redoc_regexp,
             string=referer,
             flags=re.I)
        )
    )

    ua_string = request.headers.get('user-agent')
    browser_match = re.search(browser_regexp, ua_string)
    response_type = "api"
    if swagger_static_match == False:
        if browser_match:
            response_type = "html"

    try:
        response = await call_next(request)
    except Exception as e:
        print(request.scope['endpoint'].__name__)

        response = JSONResponse(
            status_code=500,
            content={
                "detail": f"Internal server error {e}"
            }
        )
        return response

    if response.status_code == 307:
        return response
    content_type = response.headers.get('content-type')
    content_type = content_type if content_type else ""
    content_json = re.match(r"application/json", content_type)
    if all([response_type == "html",
            content_json]):
        endpoint = request.scope['endpoint'].__name__
        response_b = b""
        async for chunk in response.body_iterator:
            response_b += chunk
        response_dict = json.loads(response_b)
        modder = RESPONSE_MODDERS.get(endpoint)
        if modder is not None:
            return_response = await modder(
                request=request,
                response=response,
                data=response_dict)
            return return_response
        return_response = Response(content=response_b,
                                   status_code=response.status_code,
                                   headers=dict(response.headers),
                                   media_type=response.media_type)

        return return_response

    return response
