from pathlib import Path
from typing import Any, Annotated
from datetime import timedelta

from fastapi import BackgroundTasks, Depends, Request
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

from userprofile.orm import UserORM
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
        email: EmailModel,
        bg_task: BackgroundTasks,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    user_db = await db.execute(select(UserORM).filter(UserORM.email == email.email))
    user_db = user_db.scalars().first()
    if not user_db:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "details": f"User with email {email.email} not found"
            }
        )

    token = await auth_service.create_email_token(email=email.email,
                                                  live_time=timedelta(hours=12))
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
    user: UserORM = await auth_service.get_email_user(token=token, db=db)
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
