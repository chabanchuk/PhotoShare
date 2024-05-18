from fastapi.routing import APIRouter

router = APIRouter(prefix="/user", tags=["user profile"])


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    return {"message": "User profile - public part"}


@router.get("/profile/me")
async def get_my_profile():
    return {"message": "My profile"}


@router.post("/profile/me")
async def ceate_my_profile():
    return {"message": "My profile created"}


@router.put("/profile/me/{field}")
async def update_my_profile(field: str,
                            value: str):
    return {"message": f"My profile field {field} updated"}

@router.patch("/profile/me/{field}")
async def patch_my_profile(field: str,
                           value: str):
    return {"message": f"My profile field {field} patched"}
