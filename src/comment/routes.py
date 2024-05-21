from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from database import get_db
from comment.model import CommentModel, CommentCreate, CommentUpdate
from comment.orm import CommentORM
from photo.orm import PhotoORM
from userprofile.orm import ProfileORM


router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[CommentModel])
async def read_comments(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100):
    result = await db.execute(select(CommentORM).offset(skip).limit(limit))
    comments = result.scalars().all()
    return [CommentModel.from_orm(comment) for comment in comments]


@router.post("/", response_model=CommentModel)
async def create_comment(comment: CommentCreate, db: AsyncSession = Depends(get_db)):
    author_result = await db.execute(select(ProfileORM).where(ProfileORM.id == comment.author_profile_id))
    author = author_result.scalars().first()
    photo_result = await db.execute(select(PhotoORM).where(PhotoORM.id == comment.photo_id))
    photo = photo_result.scalars().first()

    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    db_comment = CommentORM(
        text=comment.text,
        author=author,
        photo=photo
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return CommentModel.from_orm(db_comment)


@router.get("/{comment_id}", response_model=CommentModel)
async def read_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommentORM).where(CommentORM.id == comment_id))
    db_comment = result.scalars().first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return CommentModel.from_orm(db_comment)


@router.put("/{comment_id}", response_model=CommentModel)
async def update_comment(comment_id: int, comment: CommentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommentORM).where(CommentORM.id == comment_id))
    db_comment = result.scalars().first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    for var, value in vars(comment).items():
        setattr(db_comment, var, value) if value else None

    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return CommentModel.from_orm(db_comment)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CommentORM).where(CommentORM.id == comment_id))
    db_comment = result.scalars().first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.delete(db_comment)
    await db.commit()
