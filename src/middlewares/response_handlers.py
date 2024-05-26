from typing import Any

from fastapi import Request, Response
from middlewares.registrator import register_modder


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
    # {'access_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzcGx1QGRlaG9jaGh1LmNvbSIsImlhdCI6MTcxNjcwODEyMSwiZXhwIjoxNzE2Nzk0NTIxLCJzY29wZSI6ImFjY2Vzc190b2tlbiJ9.BzxcdN_KSJf_wofbfL91ingrDqsgeEdy4Hf4bbg1ptA',
    # 'refresh_token': 'eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzcGx1QGRlaG9jaGh1LmNvbSIsImlhdCI6MTcxNjcwODEyMSwiZXhwIjoxNzE3MzEyOTIxLCJzY29wZSI6InJlZnJlc2hfdG9rZW4ifQ.CEiUEu63S8o7BCHI12R-bYSaPmhC7-b2vdhMv7RkbQ-YPzQQwbGUpXjvCGCdZYIgrCuSAyNlSCELMJ3MMW2g-A',
    # 'email_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzcGx1QGRlaG9jaGh1LmNvbSIsImlhdCI6MTcxNjcwODEyMSwiZXhwIjoxNzE2NzUxMzIxLCJzY29wZSI6ImVtYWlsX3Rva2VuIn0.JdCf4LwSxJjIFM7PQgl7aCT0rCw1Cv2QGehFWCcR_Ks',
    # 'token_type': 'bearer'}
    print(f"Response status: {response.status_code}")
    print("Response handler for auth_login", data)

    return response