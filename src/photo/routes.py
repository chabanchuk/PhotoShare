
from typing import List, Optional, Annotated, Any
import io
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, APIRouter, status, Form, Query
# from requests import HTTPError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_
import cloudinary
from cloudinary.uploader import upload, destroy
from sqlalchemy.orm import selectinload
from fastapi.responses import Response, JSONResponse
import qrcode
from database import get_db
from photo.model import PhotoResponse, PhotoUpdate, PhotoModel, TransformRequest, PhotoCreateQR
from photo.orm import PhotoORM
from tags.orm import TagORM
from userprofile.orm import ProfileORM, UserORM
from settings import settings
import qrcode.image.svg
from userprofile.orm import ProfileORM, UserORM
from auth.service import auth as auth_service


router = APIRouter(prefix='/photos', tags=["photos"])


cloudinary.config(
        cloud_name=settings.cloudinary_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )


async def get_profile(user_id: int, db: AsyncSession):
    """
        Returns the profile of a user.

        Args:
            user_id (int): The ID of the user.
            db (AsyncSession): The database session.

        Returns:
            Union[JSONResponse, ProfileORM]: If the profile is found, returns the profile.
            Otherwise, returns a JSONResponse with a 404 status code and a message "Profile not found".
    """
    query = select(ProfileORM).filter_by(user_id=user_id)
    result = await db.execute(query)
    profile = result.scalars().first()
    if profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Profile not found"}
        )
    return profile


@router.post("/add",
             response_model=PhotoResponse
             )
async def create_photo(
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        description: str = Form(),
        file: UploadFile = File(),
        tags: Annotated[str | None, Form()] = None
):

    tags_list = tags.split(' ') if tags else []
    tags_photo = []
    for tag in tags_list:
        tag_exists = await db.execute(select(TagORM).where(TagORM.tag == tag))
        tag_exists = tag_exists.scalars().first()
        if not tag_exists:
            new_tag = TagORM(tag=tag)
            db.add(new_tag)
            await db.commit()
            await db.refresh(new_tag)
            tags_photo.append(new_tag)
        else:
            tags_photo.append(tag_exists)

    profile = await get_profile(user.id, db)
    max_file_size = 3 * 1024 * 1024  # 3 megabytes
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > max_file_size:
        raise HTTPException(status_code=413,
                            detail="File size exceeds the limit of 3 megabytes")
    await file.seek(0)
    cloudinary_result = upload(file.file, folder="photos/")
    photo = PhotoModel(description=description)
    db_photo = PhotoORM(url=cloudinary_result['secure_url'],
                        public_id=cloudinary_result['public_id'],
                        description=photo.description,
                        author_fk=profile.id,
                        tags=tags_photo)
    db.add(db_photo)
    await db.commit()
    await db.refresh(db_photo)
    return PhotoResponse.from_orm(db_photo)


@router.post("/{transform}", response_model=PhotoResponse, status_code=status.HTTP_200_OK)
async def transform_photo(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)],
    photo_id: int = Form(...),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    crop: Optional[str] = Form(None),
    gravity: Optional[str] = Form(None),
    radius: Optional[str] = Form(None),
    effect: Optional[str] = Form(None),
    quality: Optional[str] = Form(None),
    brightness: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
):
    """
        Transforms a photo with the specified transformations and updates the database with the new photo details.

        Args:
            db (AsyncSession): The database session.
            user (UserORM): The authenticated user.
            photo_id (int): The ID of the photo to transform.
            width (Optional[int]): The width of the transformed photo.
            height (Optional[int]): The height of the transformed photo.
            crop (Optional[str]): The cropping parameters for the transformed
                photo.
            gravity (Optional[str]): The gravity for the cropping of the
                transformed photo.
            radius (Optional[str]): The radius for the transformation
                of the photo.
            effect (Optional[str]): The effect to apply to the photo.
            quality (Optional[str]): The quality of the transformed photo.
            brightness (Optional[str]): The brightness adjustment for the photo.
            color (Optional[str]): The color adjustment for the photo.

        Returns:
            PhotoResponse: The updated photo details.

        Raises:
            HTTPException: If the photo is not found or if there is an
                error during the transformation process.
    """
    profile = await get_profile(user.id, db)
    query = select(PhotoORM).where(and_(PhotoORM.id == photo_id,
                                        PhotoORM.author_fk == profile.id))
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    transformations = {key: value for key, value in locals().items()
                       if key != 'db'
                       and key != 'photo_id'
                       and value is not None}
    try:
        transformed_url = upload(db_photo.url, **transformations)
        destroy(db_photo.public_id)
        if db_photo.qrcode_url not in [None, '']:
            destroy(db_photo.qrcode_public_id)
        db_photo.url = transformed_url['secure_url']
        db_photo.public_id = transformed_url['public_id']
        db_photo.qrcode_url = None
        db.add(db_photo)
        await db.commit()
        await db.refresh(db_photo)
        return PhotoResponse.from_orm(db_photo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{tags}", status_code=status.HTTP_201_CREATED)
async def add_tags_to_photo(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)],
    photo_id: int = Form(...),
    tag_names: List[str] = Form(...)
):
    """
    Add tags to a photo.

    This endpoint allows the user to add up to 5 tags to a photo.

    Args:
        db (AsyncSession): The database session.
        user (UserORM): The authenticated user.
        photo_id (int): The ID of the photo to which tags will be added.
        tag_names (List[str]): A list of tag names to add to the photo.

    Returns:
        Response: A response with a 201 Created status code, indicating that the tags were successfully added.

    Raises:
        HTTPException: If the photo is not found, if the user does not have permission to add tags to the photo,
                       or if adding the tags would exceed the limit of 5 tags per photo.
    """
    profile = await get_profile(user.id, db)
    query = select(PhotoORM).where(and_(PhotoORM.id == photo_id, PhotoORM.author_fk == profile.id))
    result = await db.execute(query)
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    # Check the current number of tags and limit to 5
    if len(photo.tags) + len(tag_names) > 5:
        raise HTTPException(status_code=400, detail="Adding these tags would exceed the limit of 5 tags per photo")
    tags_to_add = await db.scalars(select(TagORM).where(TagORM.name.in_(tag_names)))
    tags_to_add = tags_to_add.all()
    photo.tags.extend(tags_to_add)
    await db.commit()

    return Response(status_code=status.HTTP_201_CREATED)


@router.patch("/{qrcode}",response_model=PhotoResponse, status_code=status.HTTP_200_OK)
async def create_photo_link_and_qrcode(db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)], photo_id: int = Form(...)):
    """
        Generates a QR code for the photo URL and updates the photo in the database with the QR code image details.

        Args:
            db (AsyncSession): The database session.
            user (UserORM): The authenticated user.
            photo_id (int): The ID of the photo for which to generate the QR code.

        Returns:
            PhotoResponse: The updated photo details, including the QR code image URL.

        Raises:
            HTTPException: If the photo is not found.
    """
    profile = await get_profile(user.id, db)
    query = select(PhotoORM).where(and_(PhotoORM.id == photo_id, PhotoORM.author_fk == profile.id))
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=5)
    qr.add_data(db_photo.url)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    # Upload the image to Cloudinary
    cloudinary_result = upload(img_bytes.read(), folder="qrcode/")
    db_photo.qrcode_url = cloudinary_result['secure_url']
    db_photo.qrcode_public_id = cloudinary_result['public_id']
    await db.commit()
    await db.refresh(db_photo)
    return PhotoResponse.from_orm(db_photo)


@router.get("/", response_model=List[PhotoResponse])
async def get_photos(limit: int = Query(10, ge=1, le=10), offset: int = Query(0, ge=0),
                     db: AsyncSession = Depends(get_db)):
    """
        Retrieves a list of photos with pagination.

        Args:
            limit (int): The maximum number of photos to return. Must be between 1 and 10.
            offset (int): The number of photos to skip before starting to collect the result set. Must be greater than or equal to 0.
            db (AsyncSession): The database session.

        Returns:
            List[PhotoResponse]: A list of photo details, limited by the `limit` and offset by the `offset`.
        """
    query = select(PhotoORM).offset(offset).limit(limit).options(
        selectinload(PhotoORM.comments),
        selectinload(PhotoORM.tags),
        selectinload(PhotoORM.author),
        selectinload(PhotoORM.author).selectinload(ProfileORM.user)
    )
    result = await db.execute(query)
    photos = result.scalars().all()
    return_list = []
    for photo in photos:
        _ = PhotoResponse.from_orm(photo)
        _.comments_num = len(photo.comments)
        _.tags = [tag.name for tag in photo.tags]
        _.author = photo.author.user.username
        return_list.append(_)

    return return_list


@router.get("/{photo_id: int}", response_model=PhotoResponse)
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    """
        Retrieves a single photo by its ID, including its comments and tags.

        Args:
            photo_id (int): The ID of the photo to retrieve.
            db (AsyncSession): The database session.

        Returns:
            PhotoResponse: The photo details, including its comments and tags.

        Raises:
            HTTPException: If the photo is not found.
    """
    query = select(PhotoORM).filter_by(id=photo_id)\
        .options(selectinload(PhotoORM.comments))
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return PhotoResponse.from_orm(db_photo)


@router.get("/tag/{tag_name: str}", response_model=List[PhotoResponse])
async def get_photos_by_tag(
    tag_name: str,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Get all photos associated with a tag.

    This endpoint allows the user to retrieve a list of photos associated with a tag specified by its name.

    Args:
        tag_name (str): The name of the tag.
        db (AsyncSession): The database session.

    Returns:
        List[PhotoResponse]: A list of photos associated with the tag.

    Raises:
        HTTPException: If the tag is not found.
    """
    tag = await db.scalar(select(TagORM).where(TagORM.name == tag_name))
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    photos = tag.photos
    return [PhotoResponse.from_orm(photo) for photo in photos]


@router.get("/user/{author_username: str}",
            response_model=List[PhotoResponse])
async def get_photos_by_author(
        author_username: str,
        db: Annotated[AsyncSession, Depends(get_db)]
) -> Any:
    """
        Retrieves a list of photos by the author's username, including their comments and tags.

        Args:
            author_username (str): The username of the author whose photos to retrieve.
            db (AsyncSession): The database session.

        Returns:
            List[PhotoResponse]: A list of photo details, including their comments and tags, authored by the specified user.

        Raises:
            HTTPException: If the user or profile is not found.
    """
    query1 = select(UserORM).where(UserORM.username == author_username)
    result = await db.execute(query1)
    user = result.scalars().first()
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"User with username: {author_username} not found"}
        )
    query2 = select(ProfileORM).filter_by(user_id=user.id)
    result = await db.execute(query2)
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    query = select(PhotoORM).where(PhotoORM.author_fk == profile.id)\
        .options(selectinload(PhotoORM.comments),
                 selectinload(PhotoORM.tags))
    result = await db.execute(query)
    photos = result.scalars().all()
    return [PhotoResponse.from_orm(photo) for photo in photos]


@router.put("/{photo_id}", response_model=PhotoResponse)
async def update_photo(db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)], photo_id: int, description: str = Form()):
    """
        Update a photo's description.

        This endpoint allows the user to update the description of a photo. The user must be an admin to update any photo,
        otherwise, they can only update their own photos.

        Args:
            db (AsyncSession): The database session.
            user (UserORM): The authenticated user.
            photo_id (int): The ID of the photo to update.
            description (str): The new description for the photo.

        Returns:
            PhotoResponse: The updated photo.

        Raises:
            HTTPException: If the photo is not found or if the user does not have permission to update the photo.
    """
    profile = await get_profile(user.id, db)
    # Check if the user's role is 'admin'
    if user.role != 'admin':
        query = select(PhotoORM).where(and_(PhotoORM.id == photo_id, PhotoORM.author_fk == profile.id))
    else:
        query = select(PhotoORM).where(PhotoORM.id == photo_id)
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    db_photo.description = description
    await db.commit()
    await db.refresh(db_photo)
    return PhotoResponse.from_orm(db_photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)], photo_id: int):
    """
        Delete a photo.

        This endpoint allows the user to delete a photo. The user must be an admin to delete any photo,
        otherwise, they can only delete their own photos.

        Args:
            db (AsyncSession): The database session.
            user (UserORM): The authenticated user.
            photo_id (int): The ID of the photo to delete.

        Returns:
            Response: A response with a 204 No Content status code, indicating that the photo was successfully deleted.

        Raises:
            HTTPException: If the photo is not found or if the user does not have permission to delete the photo.
    """
    profile = await get_profile(user.id, db)
    # Check if the user's role is 'admin'
    if user.role != 'admin':
        query = select(PhotoORM).where(and_(PhotoORM.id == photo_id, PhotoORM.author_fk == profile.id))
    else:
        query = select(PhotoORM).where(PhotoORM.id == photo_id)
    result = await db.execute(query)
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    destroy(photo.public_id)
    if photo.qrcode_url not in [None, '']:
        destroy(photo.qrcode_public_id)
    await db.delete(photo)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
