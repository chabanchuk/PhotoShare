from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, Field, PositiveInt

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
    created_at: datetime = Field(default=datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default=None)
    author_profile_id: PositiveInt
    photo_id: PositiveInt

    class Config:
        orm_mode = True