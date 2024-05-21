from datetime import datetime, timezone
from typing import Optional, List

from pydantic import (BaseModel,
                      EmailStr,
                      PastDate,
                      computed_field,
                      Field, PositiveInt, ConfigDict)

from comment.model import CommentModel
from photo.model import PhotoModel
from userprofile.orm import Role


class UserAuthModel(BaseModel):
    """
    Model that is used to meet OAuth2 requirements
    """
    username: str
    email: EmailStr
    password: str


class UserRegisterModel(BaseModel):
    """
    Model that is used to meet OAuth2 requirements
    """
    username: str
    email: EmailStr
    password: str


class UserDBModel(UserAuthModel):
    """
    Model that stores user data in DB
    """
    model_config = ConfigDict(from_attributes=True)

    id: PositiveInt
    email: EmailStr
    password: str = Field(max_length=255)
    registered_at: datetime = Field(default=datetime.now(timezone.utc))


class UserProfileModel(BaseModel):
    """
    Model that holds all user information
    """
    username: str
    first_name: str
    last_name: Optional[str]
    email: EmailStr
    birthday: Optional[PastDate]
    registered_at: datetime = Field(default=datetime.now(timezone.utc))
    role: Role = Field(default='user')
    photos: Optional[List["PhotoModel"]] = []
    comments: Optional[List["CommentModel"]] = []

    @computed_field
    @property
    def full_name(self) -> str:
        """
        Fields value is computed by concatenation of first_name
        and not empty last_name

        Returns:
            str: Full name
        """
        lname = ' ' + self.last_name if self.last_name else ''
        return self.first_name + lname


class TokenModel(BaseModel):
    access_token: str
    refresh_token: str
    email_token: str
    token_type: str = "bearer"


class UserPublicProfileModel(BaseModel):
    """
    Model that holds public user information
    """
    model_config = ConfigDict(from_attributes=True)
    username: str = Field()
    first_name: str
    last_name: Optional[str]
    registered_at: datetime = Field(default=datetime.now(timezone.utc))
    role: Role = Field(default='user')
    photos: PositiveInt = Field(default=0)
    comments: PositiveInt = Field(default=0)

    @computed_field
    @property
    def full_name(self) -> str:
        """
        Fields value is computed by concatenation of first_name
        and not empty last_name

        Returns:
            str: Full name
        """
        lname = ' ' + self.last_name if self.last_name else ''
        return self.first_name + lname


class UserEditableProfileModel(BaseModel):
    username: Optional[str] = Field(min_length=3, default=None)
    email: Optional[EmailStr] = None
    birthday: Optional[PastDate] = None
    first_name: Optional[str] = Field(min_length=3, default=None)
    last_name: Optional[str] = Field(min_length=3, default=None)
