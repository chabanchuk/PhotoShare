from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from starlette.requests import Request

from userprofile.model import TokenModel, UserAuthModel, UserDBModel
from database import get_db

from auth.service import Authentication
from email_service.routes import send_confirmation, EmailModel
from userprofile.orm import UserORM

router = APIRouter(prefix="/auth",
                   tags=["Authentication"])

auth_service = Authentication()


@router.post("/register",
             response_model=UserDBModel,
             responses={409: {"description": "User already exists"},
                        201: {"model": UserDBModel}})
async def new_user(
        user: UserAuthModel,
        db: Annotated[AsyncSession, Depends(get_db)],
        bg_task: BackgroundTasks
) -> Any:
    exists = await db.execute(select(UserORM).filter(UserORM.email == user.email))
    exists = exists.scalars().first()
    if exists:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "details": [
                    {"msg": f"User with email: {user.email} already registered"}
                ]}
        )

    hashed_pwd = auth_service.get_hash_password(user.password)
    user = UserORM(email=user.email,
                   username=user.username,
                   password=hashed_pwd)
    db.add(user)
    await db.commit()

    email_param = EmailModel(email=user.email)
    res = await send_confirmation(email=email_param,
                                  bg_task=bg_task,
                                  db=db)

    ret_user = await db.execute(select(UserORM).filter(UserORM.email == user.email))
    ret_user = ret_user.scalars().first()
    return JSONResponse(
        status_code=201,
        content={**UserDBModel.from_orm(ret_user).dict(exclude={"id"}),
                 'confirmation': res['message']}
    )


@router.post("/login",
             response_model=TokenModel)
async def login(
        user: Annotated[OAuth2PasswordRequestForm, Depends()],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Handles the login functionality for the API.

    Args:
        user (OAuth2PasswordRequestForm, optional): The user credentials for login.
            Defaults to Depends(OAuth2PasswordRequestForm).
        db (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        Any: The response containing the access token, refresh token, email token,
            and token type.

    Raises:
        JSONResponse: If the user is not found, the credentials are invalid, or the email is not confirmed.
    """
    db_response = await db.execute(select(UserORM).filter(UserORM.username == user.username))
    user_db: UserORM = db_response.scalars().first()

    if not user_db:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "details": [
                    {"msg": f"User with username: {user.username} not found"}
                ]}
        )

    if not auth_service.verify_password(user.password, user_db.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "details": [
                    {"msg": "Invalid credentials"}
                ]}
        )

    # if not user_db.email_confirmed:
    #     return JSONResponse(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         content={
    #             'details': [
    #                 {"msg": "Email not confirmed."}
    #             ]
    #         }
    #     )

    access_token = auth_service.create_access_token(user_db.email)
    refresh_token = auth_service.create_refresh_token(user_db.email)
    email_token = auth_service.create_email_token(user_db.email)

    user_db.loggedin = True
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"access_token": access_token,
                 "refresh_token": refresh_token,
                 "email_token": email_token,
                 "token_type": "bearer"}
    )


@router.post("/refresh", response_model=TokenModel)
async def refresh(
        request: Request,
        user: Annotated[UserORM, Depends(auth_service.get_refresh_user)]
) -> Any:
    """
    Refreshes the access token for the user using the provided refresh token.

    Parameters:
        request (Request): The HTTP request object.
        user (Annotated[UserORM, Depends(auth_service.get_refresh_user)]): The user object obtained from the authentication service.

    Returns:
        Any: The JSON response containing the access token, refresh token, email token, and token type.

    Raises:
        JSONResponse: If the user is not logged in or the credentials are invalid.

    This function is an API endpoint that handles the refresh of access tokens. It takes a request object and a user object obtained from the authentication service as parameters. It first checks if the user is logged in and returns a JSON response with an HTTP 401 status code and an error message if the user is not logged in. It then checks if the user's email is None and returns a JSON response with an HTTP 403 status code and an error message if the credentials are invalid. If both checks pass, it creates an access token, refresh token, and email token using the user's email. It returns a JSON response with an HTTP 200 status code and the access token, refresh token, email token, and token type.
    """
    if not user.loggedin:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"details": "User not logged in. Use /auth/login"}
        )
    if user.email is None:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"details": "Invalid credentials"}
        )
    email_str = str(user.email)
    access_token = await auth_service.create_access_token(email_str)
    refresh_token = await request.headers.get("Authorization").split(" ")[1]
    email_token = await auth_service.create_email_token(email_str)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"access_token": access_token,
                 "refresh_token": refresh_token,
                 "email_token": email_token,
                 "token_type": "bearer"}
    )


@router.get("/logout")
async def logout(
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Logs out a user by setting the 'loggedin' attribute of the UserORM object to False.

    Parameters:
        user (Annotated[UserORM, Depends(auth_service.get_access_user)]): The UserORM object representing the user
        to be logged out.
        db (Annotated[AsyncSession, Depends(get_db)]): The AsyncSession object representing the database session.

    Returns:
        Any: A dictionary containing the details of the logout operation.

    Raises:
        HTTPException: If an internal server error occurs during the logout process.
    """
    try:
        user.loggedin = False
        await db.commit()
        return {"details": "User logged out"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {e}")
