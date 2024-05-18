from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# from comment.model import CommentModel
# from tags.model import TagModel


class PhotoModel(BaseModel):
    title: str
    author_fk: int


class PhotoCreate(PhotoModel):
    pass


class PhotoUpdate(BaseModel):
    title: Optional[str] = None


class PhotoResponse(PhotoModel):
    id: int
    url: str
    comments: List["CommentModel"] = []
    tags: List["TagModel"] = []

    model_config = ConfigDict(from_attributes=True)
