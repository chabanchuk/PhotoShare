from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from comment.orm import CommentORM
from tags.orm import TagORM


class PhotoBase(BaseModel):
    title: str
    author_fk: int


class PhotoCreate(PhotoBase):
    pass


class PhotoUpdate(BaseModel):
    title: Optional[str] = None


class PhotoResponse(PhotoBase):
    id: int
    url: str
    comments: List[CommentORM] = []
    tags: List[TagORM] = []

    model_config = ConfigDict(from_attributes=True)
