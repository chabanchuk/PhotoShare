import re
from datetime import datetime, timezone

from jose import jwt
from sqlalchemy import select, or_

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status
from starlette.requests import Request

from userprofile.model import TokenModel, UserAuthModel, UserDBModel, UserRegisterModel
from database import get_db

from auth.service import auth as auth_service
from userprofile.orm import UserORM, ProfileORM

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserDBModel,
    responses={
        409: {"description": "User already exists"},
        201: {"model": UserDBModel},
    },
)
async def auth_register(
        username: Annotated[str, Form(...)],
        email: Annotated[str, Form(...)],
        password: Annotated[str, Form(...)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    exists = await db.execute(
        select(UserORM).filter(
            or_(UserORM.email == email, UserORM.username == username)
        )
    )
    exists = exists.scalars().first()
    if exists:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail":
                    {"msg": "User with such email or username already registered"}
            },
        )

    hashed_pwd = auth_service.get_hash_password(password)
    user_orm = UserORM(email=email, username=username, password=hashed_pwd)
    user_orm.profile = ProfileORM(user=user_orm)

    db.add(user_orm)
    await db.commit()
    await db.refresh(user_orm)

    ret_user = await db.execute(select(UserORM).filter(UserORM.email == email))
    ret_user = ret_user.scalars().first()
    user_db_model = UserDBModel.from_orm(ret_user)
    user_db_model.registered_at = user_db_model.registered_at.isoformat()

    return JSONResponse(
        status_code=201,
        content={
            **UserDBModel.from_orm(ret_user).model_dump(
                exclude={"id", "password", "registered_at"}
            ),
            "registered_at": str(ret_user.registered_at),
        },
    )


@router.post("/login", response_model=TokenModel)
async def auth_login(
    request: Request,
    user: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    db_response = await db.execute(
        select(UserORM).filter(UserORM.username == user.username)
    )
    user_db: UserORM = db_response.scalars().first()
    if not user_db:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": {"msg": f"User with username: {user.username} not found"}
            }
        )

    if not auth_service.verify_password(user.password, user_db.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": {"msg": "Invalid credentials"}},
        )
    iat = datetime.now(timezone.utc)
    access_token = auth_service.create_access_token(sub=user_db.email,
                                                    iat=iat)
    refresh_token = auth_service.create_refresh_token(sub=user_db.email,
                                                      iat=iat)
    email_token = auth_service.create_email_token(sub=user_db.email,
                                                  iat=iat)

    user_db.loggedin = True

    await db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "email_token": email_token,
            "token_type": "bearer",
        },
    )


@router.post("/refresh", response_model=TokenModel)
async def auth_refresh(
    request: Request,
    user: Annotated[UserORM, Depends(auth_service.get_refresh_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    if not user.loggedin:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"details": "User not logged in. Use /auth/login"},
        )

    refresh_token = request.headers.get("Authorization").split(" ")[1]
    payload = jwt.decode(
        refresh_token,
        auth_service.SECRET_512,
        algorithms=[auth_service.REFRESH_ALGORITHM],
    )

    blacklisted_tokens = await auth_service.get_blacklisted_tokens(user.email, db)
    for blacklisted_token in blacklisted_tokens:
        if blacklisted_token.expire_refresh == datetime.fromtimestamp(payload["exp"]):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"details": "Token is blacklisted"},
            )

    access_token = auth_service.create_access_token(user.email)
    email_token = auth_service.create_email_token(user.email)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "email_token": email_token,
            "token_type": "bearer",
        },
    )


@router.get("/logout")
async def auth_logout(
    token: Annotated[str, Depends(auth_service.oauth2_schema)],
    user_orm: Annotated[UserORM, Depends(auth_service.get_access_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    if not user_orm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        await auth_service.add_to_blacklist(
            token, user_orm.email, user_orm.username, db
        )
    except Exception as e:
        if re.search(r"unique constraint", str(e), re.I):
           print("Token already blacklisted")

    user_orm.loggedin = False
    await db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "details": "User logged out"
        }
    )
