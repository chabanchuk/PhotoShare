from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src.tags.model import TagModel, TagResponseModel
from src.tags.orm import TagORM

router = APIRouter()

@router.post("/tags/", response_model=TagResponseModel)
def create_or_get_tag(tag: TagModel, db: Session = Depends(get_db)):
    existing_tag = db.query(TagORM).filter(TagORM.tag == tag.tag).first()
    if existing_tag:
        return existing_tag
    new_tag = TagORM(tag=tag.tag)
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    return new_tag
