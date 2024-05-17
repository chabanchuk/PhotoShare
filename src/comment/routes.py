from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from schemas import CommentModel, CommentCreate, CommentUpdate
from models import CommentORM

router = APIRouter(
    prefix="/comments",
    tags=["comments"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[CommentModel])
def read_comments(db: Session = Depends(get_db), skip: int = 0, limit: int = 100):
    comments = db.query(CommentORM).offset(skip).limit(limit).all()
    return comments

@router.post("/", response_model=CommentModel)
def create_comment(comment: CommentCreate, db: Session = Depends(get_db)):
    db_comment = CommentORM(**comment.dict())
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("/{comment_id}", response_model=CommentModel)
def read_comment(comment_id: int, db: Session = Depends(get_db)):
    db_comment = db.query(CommentORM).filter(CommentORM.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return db_comment

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
    return db_comment

@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    db_comment = db.query(CommentORM).filter(CommentORM.id == comment_id).first()
    if db_comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    db.delete(db_comment)
    db.commit()
    return None