"""
Module provides necessary functions to compensate absence of JS skill
Because we do want to have a nice frontend without heavy React or other
js based framework with all these webpacks, nmps and so on
"""
from fastapi import Request


async def cookie_to_header_jwt(request: Request,
                               call_next):
    print("cookie_to_header_jwt")
    response = await call_next(request)
    return response


async def modify_json_response(request: Request,
                               call_next):
    response = await call_next(request)
    print("modify_json_response")
    return response
