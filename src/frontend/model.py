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

    username: str
    email: EmailStr
    role: Role
