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


# class EncodedToJSON:
#     def __init__(self, app):
#         self.app = app
#
#     async def __call__(self, scope, receive, send):
#         if scope["type"] != "http":
#             await self.app(scope, receive, send)
#             return
#
#         is_appropriate = False
#         cl_ind = None
#         for ind, header_pair in enumerate(scope.get('headers')):
#             if all((header_pair[0].decode().lower() == 'content-type',
#                     header_pair[1].decode().lower()
#                     == 'application/x-www-form-urlencoded')):
#                 scope['headers'][ind] = (b'content-type',
#                                          b'application/json')
#                 is_appropriate = True
#             if header_pair[0].decode().lower() == 'content-length':
#                 cl_ind = ind
#
#         if not is_appropriate:
#             await self.app(scope, receive, send)
#             return
#
#         async def modify_body():
#             nonlocal scope, cl_ind
#
#             message = await receive()
#             assert message["type"] == "http.request"
#
#             body: bytes = message.get("body", b"")
#             body: str = body.decode()
#             data = urllib.parse.unquote(body)
#             data = urllib.parse.parse_qsl(data)
#             data = dict((key, value) for (key, value) in data)
#
#             message["body"] = json.dumps(data).encode()
#             print(len(message))
#             scope['headers'][cl_ind] = (b'content-length',
#                                         len(message['body']))
#             return message
#
#         await self.app(scope, modify_body, send)


async def cookie_to_header_jwt(request: Request,
                               call_next):
    print("cookie_to_header_jwt")
    response = await call_next(request)
    return response


async def modify_json_response(request: Request,
                               call_next):

    browser_regexp = (r"Mozilla|Chrome|Chromium|Apple|WebKit|" +
                      r"Edge|IE|MSIE|Firefox|Gecko")
    docs_redoc_regexp = (r"/docs$|/docs#|/docs/|/redoc$|/redoc#|/redoc/"
                         + r"|/openapi.json$|/static/|/favicon.ico$")

    swagger_static_match = re.search(pattern=docs_redoc_regexp,
                                     string=str(request.url),
                                     flags=re.I)

    ua_string = request.headers.get('user-agent')
    browser_match = re.search(browser_regexp, ua_string)
    response_type = "api"
    if swagger_static_match is None:
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
        return_response = Response(content=response_b,
                                   status_code=response.status_code,
                                   headers=dict(response.headers),
                                   media_type=response.media_type)

        return return_response

    return response