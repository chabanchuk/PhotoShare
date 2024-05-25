from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class TagModel(BaseModel):
    """
    A model for a tag that represents the structure of a tag
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    tag: str = Field(min_length=1, max_length=50)
    photos_num: int = Field(default=0)


class TagCreate(BaseModel):
    tag: str = Field(min_length=1, max_length=50)


class TagResponseModel(BaseModel):
    id: int
    tag: str

    model_config = ConfigDict(from_attributes=True)
