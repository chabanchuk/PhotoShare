from datetime import datetime, timezone
from typing import Optional, List

from pydantic import (BaseModel,
                      EmailStr,
                      PastDate,
                      computed_field,
                      Field, PositiveInt)


class UserAuthModel(BaseModel):
    """
    Model that is used to meet OAuth2 requirements
    """
    username: EmailStr
    password: str


class UserDBModel(UserAuthModel):
    """
    Model that stores user data in DB
    """
    id: PositiveInt
    registered_at: datetime = Field(default=datetime.now(timezone.utc))


class UserProfileModel(BaseModel):
    """
    Model that holds all user information
    """
    first_name: str
    last_name: Optional[str]
    email: EmailStr
    birthday: Optional[PastDate]
    registered_at: datetime = Field(default=datetime.now(timezone.utc))
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
