from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.tags.model import TagModel, TagResponseModel
from src.tags.orm import TagORM
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.post("/tags/", response_model=TagResponseModel)
async def create_or_get_tag(tag: TagModel, db: AsyncSession = Depends(get_db)):
    existing_tag = await db.query(TagORM).filter(TagORM.tag == tag.tag).first()
    if existing_tag:
        return existing_tag
    new_tag = TagORM(tag=tag.tag)
    await db.add(new_tag)
    await db.commit()
    await db.refresh(new_tag)
    return new_tag