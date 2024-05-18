from pathlib import Path
from typing import Any, Annotated
from datetime import timedelta

from fastapi import BackgroundTasks, Depends
from fastapi.routing import APIRouter
from pydantic import EmailStr, BaseModel
from fastapi_mail import (ConnectionConfig,
                          MessageSchema,
                          MessageType,
                          FastMail)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import JSONResponse

from user_profile.orm import UserORM
from settings import settings
from auth.service import Authentication
from database import get_db

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


@router.post('/send-confirmation')
async def send_confirmation(
        bg_task: BackgroundTasks,
        email: EmailModel,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Sends a confirmation email to the specified email address.

    Parameters:
        - bg_task (BackgroundTasks): The background tasks to be executed.
        - email (EmailModel): The email address to send the confirmation to.
        - db (Annotated[AsyncSession, Depends(get_db)]): The database session.

    Returns:
        - Any: A JSON response indicating the success or failure of sending the email.

    Raises:
        - None

    This function sends a confirmation email to the specified email address. It first checks if the user with the given email address exists in the database. If the user is not found, it returns a JSON response with a status code of 404 and a details message indicating that the user was not found.

    If the user is found, a confirmation token is generated using the `auth_service.create_access_token` function. The token is associated with the email address and has a live time of 1 day. The token URL is generated using the `router.url_path_for` function, specifying the 'confirm_email' route and the token as a parameter.

    A message schema is created with the subject "Email confirmation", the recipient email address, a template body containing the token URL, and the subtype set to MessageType.html.

    A FastMail instance is created using the `conf` configuration. The `fm.send_message` function is called with the message, specifying the template name as "confirm_email.html". The message sending is performed as a background task using the `bg_task.add_task` function.

    Finally, a JSON response is returned with a success message indicating that the email has been sent to the specified email address.
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


@router.get('/confirm/{token:str}')
async def confirm_email(
        db: Annotated[AsyncSession, Depends(get_db)],
        token: str
) -> Any:
    """
    Confirms an email address by updating the user's email_confirmed flag in the database.

    Parameters:
        db (Annotated[AsyncSession, Depends(get_db)]): The asynchronous database session.
        token (str): The confirmation token associated with the email address.

    Returns:
        Any: A JSON response indicating the success or failure of the email confirmation.

    Raises:
        None

    If the email address is already confirmed, returns a JSON response with a status code of 409
    and a message indicating that the email is already confirmed. Otherwise, updates the
    email_confirmed flag to True and returns a JSON response with a status code of 200 and a
    message indicating that the email has been confirmed.
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
