from typing import List, Annotated, Any

from fastapi import Depends, status
from fastapi.routing import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from database import get_db
from auth.service import Authentication as auth_service
from user_profile.model import UserPublicProfileModel
from user_profile.orm import ProfileORM, UserORM


router = APIRouter(prefix="/user", tags=["user profile"])


@router.get("/profiles", response_model=List[UserPublicProfileModel])
async def get_all_profiles(
        db: Annotated[AsyncSession, Depends(get_db)],
        offset: int = 0,
        limit: int = 10
) -> Any:
    stmnt = select(ProfileORM).offset(offset).limit(limit)
    res = await db.execute(stmnt)
    res = res.scalars().all()
    if len(res) == 0:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "No profiles found"}
        )
    return [UserPublicProfileModel.from_orm(profile) for profile in res]


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    return {"message": "User profile - public part"}


@router.get("/profile/me")
async def get_my_profile():
    return {"message": "My profile"}


@router.post("/profile/me")
async def ceate_my_profile():
    return {"message": "My profile created"}


@router.put("/profile/me/{field}")
async def update_my_profile(field: str,
                            value: str):
    return {"message": f"My profile field {field} updated"}


@router.patch("/profile/me/{field}")
async def patch_my_profile(field: str,
                           value: str):
    return {"message": f"My profile field {field} patched"}
