from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from photo.orm import PhotoORM
from tags.model import TagCreate, TagResponseModel, TagModel
from tags.orm import TagORM
from typing import Annotated, Any, List
from auth.service import auth as auth_service
from auth.require_role import require_role
from userprofile.orm import UserORM

router = APIRouter(
    prefix="/tags",
    tags=["tags"]
)


@router.get("/", response_model=List[TagModel])
async def read_tags(
        db: Annotated[AsyncSession, Depends(get_db)],
        skip: int = 0,
        limit: int = 10,
) -> Any:
    result = await db.execute(select(TagORM).offset(skip).limit(limit))
    tags = result.scalars().all()
    return [TagModel.from_orm(tag) for tag in tags]


@router.post("/", response_model=TagModel)
async def create_or_get_tag(
    tag: TagCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)]
) -> Any:
    try:
        result = await db.execute(
            select(TagORM)
            .where(TagORM.tag == tag.tag)
            .options(selectinload(TagORM.photos)
                     .load_only(PhotoORM.public_id))
        )

        existing_tag = result.scalars().first()
        if existing_tag:
            ret_tag = TagModel.from_orm(existing_tag)
            ret_tag.photos_num = len(existing_tag.photos)
            return ret_tag

        new_tag = TagORM(tag=tag.tag)
        db.add(new_tag)
        await db.commit()
        await db.refresh(new_tag)
        return TagModel.from_orm(new_tag)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tag: str}", response_model=TagResponseModel)
async def read_tag(
        tag: str,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    result = await db.execute(select(TagORM).filter(TagORM.tag == tag))
    tag = result.scalars().first()
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return TagResponseModel.from_orm(tag)


@router.put("/{tag: str}", response_model=TagModel)
async def update_tag(
    tag: str,
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(require_role(["moderator", "admin"]))
):
    result = await db.execute(select(TagORM).filter(TagORM.tag == tag))
    db_tag = result.scalars().first()
    if db_tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    db_tag.name = tag.name
    await db.commit()
    await db.refresh(db_tag)
    return TagModel.from_orm(db_tag)
    

@router.delete("/{tag: str}",
               responses={
                    204: {"description": "Tag deleted"},
                     404: {"description": "Tag not found"}
                })
async def delete_tag(
    tag: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(require_role(["moderator", "admin"]))]
) -> Any:
    db_resp = await db.execute(select(TagORM).filter(TagORM.tag == tag))
    db_tag = db_resp.scalars().first()

    if tag is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Tag not found"}
        )

    await db.delete(db_tag)
    await db.commit()

    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT,
                        content={})
