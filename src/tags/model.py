from typing import List
from pydantic import BaseModel, ConfigDict
from photo.model import PhotoModel


class TagModel(BaseModel):
    """
    A model for a tag that represents the structure of a tag
    """
    name: str
    photos: List["PhotoModel"] = []  # List of photos associated with this tag
    class Config:
        """
        Adjusting the model
        """
        model_config = ConfigDict(from_attributes=True)
