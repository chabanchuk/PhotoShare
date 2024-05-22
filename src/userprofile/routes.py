from typing import List, Annotated, Any, TypeAlias, Literal

from fastapi import Depends, status
from fastapi.routing import APIRouter
from sqlalchemy import select, update, Column
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload

from database import get_db
from auth.service import Authentication
from userprofile.model import (UserPublicProfileModel,
                               UserProfileModel,
                               UserEditableProfileModel,
                               UserDBModel)
from userprofile.orm import ProfileORM, UserORM

import utils.model_utilities as model_util

auth_service = Authentication()

router = APIRouter(prefix="/user", tags=["user profile"])


ProfileEditField: TypeAlias = Literal[
    *model_util.get_model_fields(UserEditableProfileModel)
]

def get_orm_by_field(field: ProfileEditField) -> Any:
    """
    Returns ORM object by field name

        Args:
            field (ProfileEditField): field name

        Returns:
            UserORM | ProfileORM: ORM object
    """
    if field in ["username", "email"]:
        return UserORM, 'id'
    return ProfileORM, 'user_id'


@router.get("/profiles",
            response_model=List[UserPublicProfileModel])
async def get_all_profiles(
        db: Annotated[AsyncSession, Depends(get_db)],
        offset: int = 0,
        limit: int = 10
) -> Any:
    """
    Returns list of public profiles

        Args:
            offset (int): start index for pagination
            limit (in): quantity of profiles to return
            db (AsyncSession): session object used for database operations

        Returns:
            List[UserPublicProfileModel]: list of public profiles
            JSONResponse: error message if no profiles found
    """
    async with db:
        stmnt = select(ProfileORM).offset(offset).limit(limit).options(
            selectinload(ProfileORM.user),
            selectinload(ProfileORM.comments),
            selectinload(ProfileORM.photos)
        )
        res = await db.execute(stmnt)
        res = res.scalars().all()
        if len(res) == 0:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"detail": "No profiles found"}
            )
        return_res = []
        for profile in res:
            profile_dump = dict(**profile.__dict__)
            profile_dump['role'] = profile.user.role
            profile_dump['photos'] = len(profile.photos)
            profile_dump['comments'] = len(profile.comments)
            profile_dump['username'] = profile.user.username
            profile_dump['email'] = profile.user.email
            public_profile = UserPublicProfileModel(
                **profile_dump
            )
            return_res.append(public_profile)
    return return_res


@router.get("/profile/{username: str}",
            response_model=UserPublicProfileModel)
async def get_user_profile(
        username: str,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Retrieves public profile by username

        Args:
            username (int): start index for pagination
            db (AsyncSession): session object used for database operations

        Returns:
            UserPublicProfileModel: public accessible profile of user
            JSONResponse: error message if no profiles found
    """
    stmnt = select(ProfileORM)\
        .join(UserORM).filter(UserORM.username == username)\
        .options(selectinload(ProfileORM.comments),
                 selectinload(ProfileORM.photos),
                 selectinload(ProfileORM.user))
    res = await db.execute(stmnt)
    profile = res.scalars().first()
    if res is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Profile with username {username} not found"}
        )
    profile_dump = dict(**profile.__dict__)
    profile_dump['role'] = profile.user.role
    profile_dump['photos'] = len(profile.photos)
    profile_dump['comments'] = len(profile.comments)
    profile_dump['username'] = profile.user.username
    profile_dump['email'] = profile.user.email

    return UserPublicProfileModel(**profile_dump)


@router.get("/profile/me",
            response_model=UserProfileModel)
async def get_my_profile(
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[UserORM, Depends(auth_service.get_access_user)]
) -> Any:
    """
    Retrieves profile of signed user
        Args:
            db (AsyncSession): session object used for database operations
            user (UserORM): user object of authenticated user
        Returns:
            UserProfileModel: full  profile of logged user
            JSONResponse: error message if no profiles found
    """
    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id)\
        .options(
        selectinload(ProfileORM.comments),
        selectinload(ProfileORM.photos),
        selectinload(ProfileORM.user)
    )
    db_response = await db.execute(stmnt)
    profile = db_response.scalars().first()
    if profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Profile not found"}
        )
    profile_dump = dict(**profile.__dict__)
    profile_dump['username'] = user.username
    profile_dump['email'] = user.email
    profile_dump['photos'] = len(profile.photos)
    profile_dump['comments'] = len(profile.comments)
    return UserProfileModel(**profile_dump)


@router.post("/profile/me",
             responses={
                 409: {"detail": "Profile already exists."},
                 422: {"detail": "Could not process empty data."},
                 201: {"model": UserProfileModel}
             })
async def ceate_my_profile(
        profile: UserEditableProfileModel,
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Fill authenticated user profile if not exists

        Args:
            profile (UserEditableProfileModel): Model with user editable profile data
            user (UserORM): user object of authenticated user
            db (AsyncSession): session object used for database operations

        Returns:
            UserProfileModel or JSONResponse with 409 status code if profile exists
    """
    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id)
    db_res = await db.execute(stmnt)
    db_profile = db_res.scalars().first()

    if db_profile:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": (f"Profile for user {user.username} already exists."
                           + " Use /user/profile/edit with POST method")
            }
        )

    if model_util.is_model_empty(profile):
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Could not process empty data."
            }
        )

    user_update = profile.model_dump(exclude_unset=True,
                                     exclude={"first_name",
                                              "last_name",
                                              "birthday"})
    stmnt = (
        update(UserORM)
        .where(UserORM.id == user.id)
        .values(**user_update)
    )
    await db.execute(stmnt)

    profile_orm = ProfileORM(**profile.model_dump(
        exclude_unset=True,
        exclude={"username", "email"}),
        )
    profile_orm.user_id = user.id
    db.add(profile_orm)
    await db.commit()
    await db.refresh(profile_orm)

    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id) \
        .options(
        selectinload(ProfileORM.comments),
        selectinload(ProfileORM.photos),
        selectinload(ProfileORM.user)
    )
    db_response = await db.execute(stmnt)
    profile = db_response.scalars().first()
    if profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Profile not found"}
        )
    profile_dump = dict(**profile.__dict__)
    profile_dump['username'] = user.username
    profile_dump['email'] = user.email
    profile_dump['photos'] = len(profile.photos)
    profile_dump['comments'] = len(profile.comments)
    return UserProfileModel(**profile_dump)


@router.patch("/profile/me/{field}",
            response_model=UserProfileModel)
async def patch_my_profile_field(
        field: ProfileEditField,
        value: Any,
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
    Change authenticated user profile field value

        Args:
            field (ProfileEditField): field of profile to update
            value (Any): new value for field
            user (UserORM): user object of authenticated user
            db (AsyncSession): session object used for database operations

        Returns:
            UserProfileModel or JSONResponse with 404 status code if profile not found
            JSONResponse with 405 status code if field is not set,
            JSONResponse with 409 status code if profile exists,
            JSONResponse with 422 status code if field or value are invalid
        """
    orm_model, id_column = get_orm_by_field(field)
    stmnt = select(orm_model).filter(Column(id_column) == user.id)
    db_res = await db.execute(stmnt)
    db_model = db_res.scalars().first()

    if db_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Data for user {user.username} not found."
            }
        )

    if db_model.__dict__[field] is None:
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={
                "detail": (f"Field {field} is not set in profile."
                           + " Use PUT method to set it.")
            }
        )
    try:
        update_model = UserEditableProfileModel(**{field: value})
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": f"Value {value} is invalid for {field}."
            }
        )
    update_values = update_model.model_dump(exclude_unset=True)
    stmnt = (
         update(orm_model)
         .where(Column(id_column) == user.id)
         .values(**update_values)
    )
    res = await db.execute(stmnt)

    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id) \
        .options(
        selectinload(ProfileORM.comments),
        selectinload(ProfileORM.photos),
        selectinload(ProfileORM.user)
    )

    db_response = await db.execute(stmnt)
    db_profile = db_response.scalars().first()
    profile_dump = dict(**db_profile.__dict__)
    profile_dump['username'] = db_profile.user.username
    profile_dump['email'] = db_profile.user.email
    profile_dump['photos'] = len(db_profile.photos)
    profile_dump['comments'] = len(db_profile.comments)

    return UserProfileModel(**profile_dump)


@router.put("/profile/me/{field}",
            response_model=UserProfileModel)
async def set_my_profile_field(
        field: ProfileEditField,
        value: Any,
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Fill authenticated user profile field

        Args:
            field (ProfileEditField): field of profile to update
            value (Any): new value for field
            user (UserORM): user object of authenticated user
            db (AsyncSession): session object used for database operations

        Returns:
            UserProfileModel or JSONResponse with 404 status code if profile not found
            JSONResponse with 405 status code if field is set,
            JSONResponse with 409 status code if profile exists,
            JSONResponse with 422 status code if field or value are invalid
        """
    orm_model, id_column = get_orm_by_field(field)
    stmnt = select(orm_model).filter(Column(id_column) == user.id)
    db_res = await db.execute(stmnt)
    db_model = db_res.scalars().first()

    if db_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Data for user {user.username} not found."
            }
        )

    if db_model.__dict__[field] is not None:
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={
                "detail": (f"Field {field} is set."
                           + " Use PATCH method to change it.")
            }
        )
    try:
        update_model = UserEditableProfileModel(**{field: value})
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": f"Value {value} is invalid for {field}."
            }
        )

    update_values = update_model.model_dump(exclude_unset=True)
    stmnt = (
        update(orm_model)
        .where(Column(id_column) == user.id)
        .values(**update_values)
    )
    res = await db.execute(stmnt)

    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id) \
        .options(
        selectinload(ProfileORM.comments),
        selectinload(ProfileORM.photos),
        selectinload(ProfileORM.user)
    )

    db_response = await db.execute(stmnt)
    db_profile = db_response.scalars().first()
    profile_dump = dict(**db_profile.__dict__)
    profile_dump['username'] = db_profile.user.username
    profile_dump['email'] = db_profile.user.email
    profile_dump['photos'] = len(db_profile.photos)
    profile_dump['comments'] = len(db_profile.comments)

    return UserProfileModel(**profile_dump)


@router.patch("/profile/me",
              response_model=UserProfileModel)
async def patch_my_profile(
        profile_data: UserEditableProfileModel,
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Edit authenticated user profile

        Args:
            profile_data (UserEditableProfileModel): profile data to store
            user (UserORM): user object of authenticated user
            db (AsyncSession): session object used for database operations

        Returns:
            UserProfileModel or JSONResponse with 404 status code if profile not found.
            JSONResponse with 405 status code if profile is not set,
            JSONResponse with 422 status code if fields or values are invalid
        """
    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id)
    db_res = await db.execute(stmnt)
    db_profile = db_res.scalars().first()

    if db_profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Profile for user {user.username} not found."
            }
        )

    if model_util.is_model_empty(profile_data):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Could not process empty data."
            }
        )

    user_update = profile_data.model_dump(
        exclude_unset=True,
        exclude={"first_name",
                 "last_name",
                 "birthday"})

    if user_update:
        stmnt = (
            update(UserORM)
            .where(UserORM.id == user.id)
            .values(**user_update)
        )
        await db.execute(stmnt)

    profile_update = profile_data.model_dump(
        exclude_unset=True,
        exclude={"username", "email"})

    if profile_update:
        stmnt = (
            update(ProfileORM)
            .where(ProfileORM.id == user.id)
            .values(**profile_update)
        )
        await db.execute(stmnt)

    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id) \
        .options(
        selectinload(ProfileORM.comments),
        selectinload(ProfileORM.photos),
        selectinload(ProfileORM.user)
    )
    db_response = await db.execute(stmnt)
    db_profile = db_response.scalars().first()

    profile_dump = dict(**db_profile.__dict__)
    profile_dump['username'] = db_profile.user.username
    profile_dump['email'] = db_profile.user.email
    profile_dump['photos'] = len(db_profile.photos)
    profile_dump['comments'] = len(db_profile.comments)

    return UserProfileModel(**profile_dump)


@router.delete("/profile/me/{field}",
               response_model=UserProfileModel)
async def delete_my_profile_field(
        field: ProfileEditField,
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """Delete authenticated user profile data in field

        Args:
            field (ProfileEditField): field of profile to delete
            user (UserORM): user object of authenticated user
            db (AsyncSession): session object used for database operations

        Returns:
            UserProfileModel or JSONResponse with 404 status code if profile not found
            JSONResponse with 405 status code if field is not set
        """
    if field == "username":
        return JSONResponse(
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            content={
                "detail": "Deletion of profile fields is not allowed."
            }
        )

    orm_model, id_column = get_orm_by_field(field)
    stmnt = select(orm_model).filter(Column(id_column) == user.id)
    db_res = await db.execute(stmnt)
    db_model = db_res.scalars().first()

    if db_model is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Data for user {user.username} not found."
            }
        )

    if db_model.__dict__[field] is None:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": f"Field {field} is not set. Nothing to do."
            }
        )

    stmnt = (update(orm_model)
             .where(Column(id_column) == user.id)
             .values(**{field: None}))
    await db.execute(stmnt)
    await db.flush(orm_model)

    stmnt = select(ProfileORM).filter(ProfileORM.user_id == user.id)
    db_response = await db.execute(stmnt)
    db_profile = db_response.scalars().first()

    profile_dump = dict(**db_profile.__dict__)
    profile_dump['username'] = db_profile.user.username
    profile_dump['email'] = db_profile.user.email
    profile_dump['photos'] = len(db_profile.photos)
    profile_dump['comments'] = len(db_profile.comments)

    return UserProfileModel(**profile_dump)


@router.delete("/profile/{username}",
                responses={
                    204: {"detail": "Profile deleted"},
                    404: {"detail": "Profile not found"}
                })
async def delete_profile(
        username: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[UserORM, Depends(auth_service.get_access_user)]
) -> Any:
    """Delete user profile by username

        Args:
            username (str): username of profile to delete
            db (AsyncSession): session object used for database operations
            user (UserORM): user object of authenticated user

        Returns:
            JSONResponse with 204 status code if profile deleted
            JSONResponse with 404 status code if profile not found
        """
    stmnt = select(ProfileORM).join(UserORM).filter(UserORM.username == username)
    db_res = await db.execute(stmnt)
    db_profile = db_res.scalars().first()

    if db_profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": f"Profile with username {username} not found."
            }
        )

    if db_profile.user_id != user.id:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": "You can delete only your profile."
            }
        )

    await db.delete(db_profile)
    await db.commit()

    return JSONResponse(
        status_code=status.HTTP_204_NO_CONTENT,
        content={
            "detail": "Profile deleted."
        }
    )
