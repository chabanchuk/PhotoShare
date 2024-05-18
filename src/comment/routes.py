from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from comment.model import CommentModel, CommentCreate, CommentUpdate
from comment.orm import CommentORM
from photo.orm import PhotoORM
from user_profile.orm import ProfileORM

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[CommentModel])
def read_comments(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    comments = db.query(CommentORM).offset(skip).limit(limit).all()
    # return comments
    print(comments)
    return [CommentModel.from_orm(comment) for comment in comments]


@router.post("/", response_model=CommentModel)
def create_comment(comment: CommentCreate, db: Session = Depends(get_db)):
    author = db.query(ProfileORM).filter(ProfileORM.id == comment.author_profile_id).first()
    photo = db.query(PhotoORM).filter(PhotoORM.id == comment.photo_id).first()

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
    db.commit()
    db.refresh(db_comment)
    return CommentModel.from_orm(db_comment)


@router.get("/{comment_id}", response_model=CommentModel)
def read_comment(comment_id: int, db: Session = Depends(get_db)):
    db_comment = db.query(CommentORM).filter(CommentORM.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return CommentModel.from_orm(db_comment)


@router.put("/{comment_id}", response_model=CommentModel)
def update_comment(comment_id: int, comment: CommentUpdate, db: Session = Depends(get_db)):
    db_comment = db.query(CommentORM).filter(CommentORM.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")

    for var, value in vars(comment).items():
        setattr(db_comment, var, value) if value else None

    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return CommentModel.from_orm(db_comment)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    db_comment = db.query(CommentORM).filter(CommentORM.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(db_comment)
    db.commit()
