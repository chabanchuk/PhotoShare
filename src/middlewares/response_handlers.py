from typing import Any

from fastapi import Request, Response
from middlewares.registrator import register_modder


@register_modder('get_my_profile')
async def html_get_my_profile(response: Response,
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
