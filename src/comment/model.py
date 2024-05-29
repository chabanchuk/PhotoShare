from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, PositiveInt, ConfigDict


class CommentBase(BaseModel):
    """
    Base model for a comment
    """
    text: str = Field(min_length=1)


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
    author_name: str = Field(default=None)
    author_fk: int
    photo_fk: int
