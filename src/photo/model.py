from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field
#from comment.model import CommentModel
#from tags.model import TagModel


class PhotoModel(BaseModel):
    description: str = Field(min_length=1, max_length=255)


class TransformRequest(BaseModel):
    width: Optional[int] = Field(None, ge=1)
    height: Optional[int] = Field(None, ge=1)
    crop: Optional[str] = None
    gravity: Optional[str] = None
    radius: Optional[str] = None
    effect: Optional[str] = None
    quality: Optional[str] = None
    brightness: Optional[str] = None
    color: Optional[str] = None


class PhotoCreateQR(BaseModel):
    qrcode_url: Optional[str] = None


class PhotoUpdate(BaseModel):
    description: Optional[str] = None


class PhotoResponse(PhotoModel):
    id: int
    author: Any
    url: str
    author_fk: int
    public_id: str
    qrcode_url: Optional[str]
    comments_num: int = Field(ge=0, default=0)
    tags: list[Any] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class QRCodeModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    qrcode_url: str
    url: str
