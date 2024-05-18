import bcrypt
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi_limiter.depends import RateLimiter
from fastapi.responses import JSONResponse
from starlette import status
from starlette.requests import Request

from src.user_profile.model import TokenModel, UserAuthModel, UserDBModel
from src.database import get_db

from src.auth.service import Authentication
from src.email_service.routes import send_confirmation, EmailModel
from src.user_profile.orm import UserORM

router = APIRouter(prefix="/auth",
                   tags=["Authentication"])

auth_service = Authentication()


@router.post("/users/", response_model=UserAuthModel)
async def create_user(username: str, password: str, db: AsyncSession = Depends(get_db)):
    """
    Creates a new user in the database with the given username and password.

    Parameters:
        - username (str): The username of the new user.
        - password (str): The password of the new user.
        - db (AsyncSession, optional): The database session to use. Defaults to the result of the `get_db` dependency.

    Returns:
        - UserAuthModel: The newly created user with their authentication information.

    Raises:
        - None

    Note:
        - The password is hashed before being stored in the database.
        - The password is converted to bytes before hashing.
        - The hashed password is converted back to a string after hashing.
        - The new user is added to the database.
        - The database is committed.
        - The newly created user is refreshed from the database.
    """
    # We need to hash the password before storing it
    # We convert the password string into bytes before hashing
    hashed_password_bytes = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    # Return the bytes to the string after hashing
    hashed_password = hashed_password_bytes.decode()
    new_user = UserORM(username=username, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/register",
             response_model=UserDBModel,
             responses={409: {"description": "User already exists"},
                        201: {"model": UserDBModel}},
             dependencies=[Depends(RateLimiter(times=2, seconds=10))])
async def new_user(
        user: UserAuthModel,
        db: Annotated[AsyncSession, Depends(get_db)],
        bg_task: BackgroundTasks
) -> Any:
    """
    Creates a new user with the provided authentication information.

    Parameters:
        - user (UserAuthModel): The authentication information of the user.
        - db (Annotated[AsyncSession, Depends(get_db)]): The database session.
        - bg_task (BackgroundTasks): The background tasks to be executed.

    Returns:
        - Any: A JSON response with the newly created user's information if the user was successfully created.
              If the user already exists, returns a JSON response with a 409 status code and a details message.

    Raises:
        - None

    Note:
        - This function checks if the user already exists in the database before creating a new user.
        - The password is hashed before being stored in the database.
        - The email confirmation process is triggered after creating the user.
        - The newly created user's information is returned in the JSON response.
        - The confirmation message is also included in the JSON response.
    """
    exists = await db.execute(select(UserORM).filter(UserORM.email == user.email)).scalars().first()
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
                   hashed_pwd=hashed_pwd)
    db.add(user)
    await db.commit()

    email_param = EmailModel(email=user.email)
    res = await send_confirmation(email=email_param,
                                  bg_task=bg_task,
                                  db=db)

    ret_user = await db.execute(select(UserORM).filter(UserORM.email == user.email)).scalars().first()

    return JSONResponse(
        status_code=201,
        content={**UserDBModel.from_orm(ret_user).dict(exclude={"id"}),
                 'confirmation': res['message']}
    )


@router.post("/login",
             response_model=TokenModel,
             dependencies=[Depends(RateLimiter(times=2, seconds=10))])
async def login(
        user: UserAuthModel,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Logs in a user with the provided email and password.

    Args:
        user (UserAuthModel): The user authentication model containing the email and password.
        db (Annotated[AsyncSession, Depends(get_db)]): The database session for executing the database queries.

    Returns:
        Any: The JSON response containing the access token, refresh token, email token, and token type.

    Raises:
        JSONResponse: If the user with the provided email is not found, if the credentials are invalid, or if the
        email is not confirmed.

    """
    user_db: UserORM = await db.execute(select(UserORM).filter(UserORM.email == user.email)).scalars().first()
    if not user_db:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "details": [
                    {"msg": f"User with email: {user.email} not found"}
                ]}
        )

    if not auth_service.verify_password(user.password, user_db.hashed_pwd):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "details": [
                    {"msg": "Invalid credentials"}
                ]}
        )

    if not user_db.email_confirmed:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                'details': [
                    {"msg": "Email not confirmed."}
                ]
            }
        )

    access_token = auth_service.create_access_token(user.email)
    refresh_token = auth_service.create_refresh_token(user.email)
    email_token = auth_service.create_email_token(user.email)
    user_db.loggedin = True
    await db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"access_token": access_token,
                 "refresh_token": refresh_token,
                 "email_token": email_token,
                 "token_type": "bearer"}
    )


@router.post("/refresh",
             response_model=TokenModel,
             dependencies=[Depends(RateLimiter(times=2, seconds=10))])
async def refresh(
        request: Request,
        user: Annotated[UserORM, Depends(auth_service.get_refresh_user)]
) -> Any:
    """
    Refreshes the access token for a user.

    This endpoint allows a user to refresh their access token by providing a valid refresh token.
    The user's email is extracted from the refresh token and used to generate a new access token.
    The refresh token is extracted from the request headers.

    Parameters:
        - request (Request): The incoming request object.
        - user (Annotated[UserORM, Depends(auth_service.get_refresh_user)]): The user object obtained from the
        dependency injection.

    Returns:
        - Any: The JSON response containing the refreshed access token, refresh token, email token, and token type.

    Raises:
        - JSONResponse: If the user is not logged in, if the user has invalid credentials, or if the email is
        not confirmed.

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
    access_token = auth_service.create_access_token(email_str)
    refresh_token = request.headers.get("Authorization").split(" ")[1]
    email_token = auth_service.create_email_token(email_str)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"access_token": access_token,
                 "refresh_token": refresh_token,
                 "email_token": email_token,
                 "token_type": "bearer"}
    )


@router.get("/logout",
            dependencies=[Depends(RateLimiter(times=2, seconds=10))])
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

