from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from tags.model import TagModel, TagCreate, TagResponseModel
from tags.orm import TagORM
from typing import List, Any
from auth.service import Authentication
from userprofile.orm import UserORM
from pydantic import Annotated

router = APIRouter(
    prefix="/tags",
    tags=["tags"],
    responses={404: {"description": "Not found"}},
)

auth_service = Authentication()

def require_role(allowed_roles: List[str]):
    def role_checker(user: UserORM = Depends(auth_service.get_access_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return user
    return role_checker

@router.post("/", response_model=TagResponseModel)
async def create_or_get_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(["registered user", "moderator", "admin"]))
):
    async with db as session:
        try:
            result = await session.execute(select(TagORM).filter(TagORM.name == tag.name))
            existing_tag = result.scalars().first()
            if existing_tag:
                return existing_tag
            new_tag = TagORM(name=tag.name, owner_id=current_user.id)
            session.add(new_tag)
            await session.commit()
            await session.refresh(new_tag)
            return new_tag
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TagResponseModel])
async def read_tags(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    async with db as session:
        result = await session.execute(select(TagORM).offset(skip).limit(limit))
        tags = result.scalars().all()
        return tags

@router.get("/{tag_id}", response_model=TagResponseModel)
async def read_tag(tag_id: int, db: AsyncSession = Depends(get_db)):
    async with db as session:
        result = await session.execute(select(TagORM).filter(TagORM.id == tag_id))
        tag = result.scalars().first()
        if tag is None:
            raise HTTPException(status_code=404, detail="Tag not found")
        return tag

@router.put("/{tag_id}", response_model=TagResponseModel)
async def update_tag(
    tag_id: int,
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(["registered user", "moderator", "admin"]))
):
    async with db as session:
        result = await session.execute(select(TagORM).filter(TagORM.id == tag_id))
        db_tag = result.scalars().first()
        if db_tag is None:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        db_tag.name = tag.name
        await session.commit()
        await session.refresh(db_tag)
        return db_tag

@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    current_user: Annotated[UserORM, Depends(auth_service.get_access_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    tag = await db.execute(select(TagORM).filter(TagORM.id == tag_id))
    tag = tag.scalars().first()

    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    if not await auth_service.has_access_to_delete_tag(current_user, tag.owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await db.delete(tag)
    await db.commit()

    return {"detail": "Tag deleted successfully"}
