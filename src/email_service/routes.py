from pathlib import Path
from typing import Any, Annotated
from datetime import timedelta

from fastapi import BackgroundTasks, Depends
from fastapi.routing import APIRouter
from fastapi_limiter.depends import RateLimiter
from pydantic import EmailStr, BaseModel
from fastapi_mail import (ConnectionConfig,
                          MessageSchema,
                          MessageType,
                          FastMail)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import JSONResponse

from src.user_profile.orm import UserORM
from src.settings import settings
from src.auth.service import Authentication
from src.database import get_db

auth_service = Authentication()

router = APIRouter(prefix="/email",
                   tags=["email calls"])


class EmailModel(BaseModel):
    email: EmailStr


conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_user,
    MAIL_PASSWORD=settings.mail_pass,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME="PhotoShare",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / 'templates',
)


@router.post('/send-confirmation',
             dependencies=[Depends(RateLimiter(times=2, seconds=10))])
async def send_confirmation(
        bg_task: BackgroundTasks,
        email: EmailModel,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Sends a confirmation email to the specified email address.

    Parameters:
        - bg_task (BackgroundTasks): An instance of the BackgroundTasks class for scheduling background tasks.
        - email (EmailModel): The email address to send the confirmation email to.
        - db (Annotated[AsyncSession, Depends(get_db)]): The asynchronous session dependency for interacting with
        the database.

    Returns:
        - Any: The response object containing the result of the email sending operation.

    Raises:
        - JSONResponse: If the user with the specified email address is not found in the database.

    Dependencies:
        - Depends(RateLimiter(times=2, seconds=10)): A rate limiter dependency to limit the number of requests per
        time interval.

    Steps:
        1. Query the database for the user with the specified email address.
        2. If the user is not found, return a JSONResponse with a 404 status code and a details message.
        3. Generate an access token with a live time of 1 day for the specified email address.
        4. Generate the URL path for the confirm_email endpoint with the access token.
        5. Create a MessageSchema object with the subject, recipients, template_body, and subtype.
        6. Create an instance of the FastMail class with the provided configuration.
        7. Schedule a background task to send the message using the FastMail instance.
        8. Return a dictionary with a success message.
    """
    user_db: UserORM = await db.execute(select(UserORM).filter(UserORM.email == email)).scalars().first()
    if not user_db:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "details": f"User with email {email.email} not found"
            }
        )

    token = auth_service.create_access_token(email=email.email,
                                             live_time=timedelta(days=1))
    token_url = router.url_path_for('confirm_email',
                                    token=token)
    message = MessageSchema(
        subject="Email confirmation",
        recipients=[email.email],
        template_body={"token_url": token_url},
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    bg_task.add_task(fm.send_message,
                     message,
                     template_name="confirm_email.html")

    return {"message": f"email has been sent to {email.email}"}


@router.get('/confirm/{token:str}',
            dependencies=[Depends(RateLimiter(times=2, seconds=10))])
async def confirm_email(
        db: Annotated[AsyncSession, Depends(get_db)],
        token: str
) -> Any:
    """
    Confirm the email associated with the given token.

    Parameters:
        - db (Annotated[AsyncSession, Depends(get_db)]): The asynchronous session dependency for interacting with
        the database.
        - token (str): The token used to confirm the email.

    Returns:
        - Any: The response object containing the result of the email confirmation.

    Raises:
        - JSONResponse: If the email is already confirmed.

    Dependencies:
        - Depends(RateLimiter(times=2, seconds=10)): A rate limiter dependency to limit the number of requests per
        time interval.

    Steps:
        1. Retrieve the user associated with the given token from the database.
        2. If the user's email is already confirmed, return a JSONResponse with a 409 status code and a details message.
        3. Set the email_confirmed attribute of the user to True.
        4. Commit the changes to the database.
        5. Return a JSONResponse with a 200 status code and a details message indicating the successful confirmation
        of the email.
    """
    user: UserORM = await auth_service.get_access_user(token=token, db=db)
    if user.email_confirmed:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "details": f"The email {user.email} is already confirmed."
            }
        )

    user.email_confirmed = True
    await db.commit()
    return JSONResponse(
        status_code=200,
        content={
            "details": f"The email {user.email} has been confirmed."
        }
    )
