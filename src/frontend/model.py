from pydantic import (BaseModel,
                      Field,
                      PositiveInt,
                      ConfigDict,
                      EmailStr)

from userprofile.orm import Role


class UserFrontendModel(BaseModel):
    """
    Model to use in frontend endpoints
    """
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    username: str
    email: EmailStr
    role: Role
    profile_id: PositiveInt = Field(default=None)


class UserPhotoReviewModel(UserFrontendModel):
    """Model to use in PhotoDetailedView"""
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    can_comment: bool = Field(default=True)
