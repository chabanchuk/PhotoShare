from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Annotated, Any
from datetime import datetime, timezone
from database import get_db
from comment.model import CommentModel, CommentCreate, CommentUpdate
from comment.orm import CommentORM
from photo.orm import PhotoORM
from userprofile.orm import ProfileORM, UserORM
from auth.service import auth as auth_service
from auth.require_role import require_role


router = APIRouter(
    prefix="/comments",
    tags=["comments"]
)

@router.get("/",
            response_model=List[CommentModel])
async def read_comments(
        db: AsyncSession = Depends(get_db),
        skip: int = 0,
        limit: int = 10):
    """
    Read a list of comments.
    - **skip**: Number of records to skip for pagination.
    - **limit**: Maximum number of records to return.
    """
    stmt = select(CommentORM).offset(skip).limit(limit)
    result = await db.execute(stmt)
    comments = result.scalars().all()
    return [CommentModel.from_orm(comment) for comment in comments]


@router.get("/{comment_id}",
            response_model=CommentModel)
async def get_comment(
        comment_id: int,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Get a specific comment by ID.
    - **comment_id**: ID of the comment to retrieve.
    """
    stmt = select(CommentORM).where(CommentORM.id == comment_id)
    db_resp = await db.execute(stmt)
    db_comment = db_resp.scalars().first()

    if db_comment is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Comment with id: {comment_id} not found."
            }
        )

    return CommentModel.from_orm(db_comment)


@router.post("/{photo_id}",
             response_model=CommentModel)
async def create_comment(
        comment: CommentCreate,
        photo_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[UserORM, Depends(auth_service.get_access_user)]
) -> Any:
    """
    Create a new comment for a specific photo.
    - **comment**: Comment data.
    - **photo_id**: ID of the photo to comment on.
    """
    stmt = select(ProfileORM).filter(ProfileORM.user_id == user.id)
    db_resp = await db.execute(stmt)
    db_profile = db_resp.scalars().first()
    
    if db_profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"User with username {user.username} not found."
            }
        )

    stmt = select(PhotoORM).where(PhotoORM.id == photo_id)
    db_resp = await db.execute(stmt)
    db_photo = db_resp.scalars().first()

    if db_photo is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Poto with id: {photo_id} not found."
            }
        )

    if db_photo.author_fk == db_profile.id:
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={
                "detail": "Author is not permitted to comment his photos."
            }
        )

    db_comment = CommentORM(
        text=comment.text,
        author_fk=db_profile.id,
        photo_fk=photo_id,
        created_at=datetime.now(timezone.utc)
    )

    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)

    return CommentModel.from_orm(db_comment)


@router.patch("/{comment_id}",
              response_model=CommentModel)
async def update_comment(
        comment_id: int,
        comment: CommentUpdate,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[UserORM, Depends(auth_service.get_access_user)]
) -> Any:
    """
    Update an existing comment.
    - **comment_id**: ID of the comment to update.
    - **comment**: Updated comment data.
    """
    stmt = select(CommentORM).where(CommentORM.id == comment_id)
    db_resp = await db.execute(stmt)
    db_comment = db_resp.scalars().first()

    if db_comment is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": "Comment not found."
            }
        )

    stmt_profile = select(ProfileORM).where(ProfileORM.user_id == user.id)
    db_resp_profile = await db.execute(stmt_profile)
    db_profile = db_resp_profile.scalars().first()

    if db_profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"User with username: {user.username} not found."
            }
        )

    if db_profile.id != db_comment.author_fk:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": ("Only authors and moderators"
                           " are allowed to edit comments.")
            }
        )

    if comment.text:
        db_comment.text = comment.text
        db_comment.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_comment)

    return CommentModel.from_orm(db_comment)


@router.delete("/delete/{comment_id}")
async def delete_comment(
        comment_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[
            UserORM,
            Depends(require_role(["moderator", "admin"]))
        ]
) -> Any:
    """
    Delete a comment.
    - **comment_id**: ID of the comment to delete.
    """
    stmt = select(CommentORM).where(CommentORM.id == comment_id)
    db_resp = await db.execute(stmt)
    db_comment = db_resp.scalars().first()

    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    if user.role not in ["moderator", "admin"]:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    await db.delete(db_comment)
    await db.commit()
    return None
