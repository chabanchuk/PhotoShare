from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from userprofile.orm import UserORM
from auth.service import Authentication

auth_service = Authentication()


def require_role(allowed_roles: list[str] = ["user"]):
    async def role_dependency(
            current_user: Annotated[UserORM, Depends(auth_service.get_access_user)]
    ) -> Any:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Granted role has insufficient permissions."
            )
        return current_user
    return role_dependency
