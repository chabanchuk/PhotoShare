from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# from comment.model import CommentModel
# from tags.model import TagModel


class PhotoModel(BaseModel):
    description: str = Field(min_length=3, max_length=250)


class TransformRequest(BaseModel):
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)
    crop: Optional[str] = None
    gravity: Optional[str] = None
    radius: Optional[str] = None
    effect: Optional[str] = None
    quality: Optional[str] = None
    format: Optional[str] = None


class PhotoCreate(PhotoModel):
    pass


class PhotoUpdate(BaseModel):
    description: Optional[str] = None


class PhotoResponse(PhotoModel):
    id: int
    url: str
    author_fk: int
    public_id: str
    #comments: List["CommentModel"] = []
    #tags: List["TagModel"] = []

    model_config = ConfigDict(from_attributes=True)
