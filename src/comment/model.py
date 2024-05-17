from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, PositiveInt
from photo.model import PhotoModel
from user_profile.model import UserProfileModel


class CommentBase(BaseModel):
    """
    Base model for a comment
    """
    text: str

class CommentCreate(CommentBase):
    """
    Model for creating a new comment
    """
    pass

class CommentUpdate(CommentBase):
    """
    Model for updating an existing comment
    """
    pass

class CommentModel(CommentBase):
    """
    Model for a comment in the database
    """
    id: PositiveInt
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    author: UserProfileModel
    photo: PhotoModel

    class Config:
        orm_mode = True
