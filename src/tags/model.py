from typing import List, Optional
from pydantic import BaseModel, Field

class TagModel(BaseModel):
    """
    A model for a tag that represents the structure of a tag
    """
    id: int
    name: str = Field(min_length=1, max_length=50)
    owner_id: int
    photos: Optional[List[int]] = []  # List of photo IDs associated with this tag

class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)

class TagResponseModel(BaseModel):
    id: int
    name: str
    owner_id: int

    class Config:
        orm_mode = True
