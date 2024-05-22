from fastapi import Depends, HTTPException, status
from userprofile.orm import UserORM
from auth.service import Authentication

def require_role(allowed_roles: list[str]):
    def role_dependency(current_user: UserORM = Depends(Authentication().get_access_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_dependency
