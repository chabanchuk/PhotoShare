from datetime import datetime, timezone
from typing import Optional, Type, Annotated
from pydantic import BaseModel, Field, PositiveInt, ConfigDict
import photo.model as photo_models
import userprofile.model as user_models


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
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    created_at: datetime
    updated_at: Optional[datetime] = Field(default=None)
    author_fk: int
    photo_fk: int
