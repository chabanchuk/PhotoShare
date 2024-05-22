
from typing import List, Optional, Annotated
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
from userprofile.orm import ProfileORM, UserORM
from settings import settings
import qrcode.image.svg
from userprofile.orm import ProfileORM, UserORM
from auth.service import Authentication

auth_service = Authentication()

router = APIRouter(prefix='/photos', tags=["photos"])


cloudinary.config(
        cloud_name=settings.cloudinary_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )


async def get_profile(user_id: int, db: AsyncSession):
    query = select(ProfileORM).filter_by(user_id=user_id)
    result = await db.execute(query)
    profile = result.scalars().first()
    if profile is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "Profile not found"}
        )
    return profile


@router.post("/", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def create_photo(
        db: Annotated[AsyncSession, Depends(get_db)],
        user: Annotated[UserORM, Depends(auth_service.get_access_user)],
        description: str = Form(),
        file: UploadFile = File()
):
    profile = await get_profile(user.id, db)
    max_file_size = 3 * 1024 * 1024  # 3 megabytes
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > max_file_size:
        raise HTTPException(status_code=413, detail="File size exceeds the limit of 3 megabytes")
    await file.seek(0)
    cloudinary_result = upload(file.file, folder="photos/")
    photo = PhotoModel(description=description)
    db_photo = PhotoORM(url=cloudinary_result['secure_url'], public_id=cloudinary_result['public_id'],
            description=photo.description, author_fk=profile.id)
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
    profile = await get_profile(user.id, db)
    query = select(PhotoORM).where(and_(PhotoORM.id == photo_id, PhotoORM.author_fk == profile.id))
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    transformations = {key: value for key, value in locals().items() if key != 'db' and key != 'photo_id' and value is not None}
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


@router.patch("/{qrcode}",response_model=PhotoResponse, status_code=status.HTTP_200_OK)
async def create_photo_link_and_qrcode(db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)], photo_id: int = Form(...)):
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
    query = select(PhotoORM).offset(offset).limit(limit)
    result = await db.execute(query)
    photos = result.scalars().all()
    return [PhotoResponse.from_orm(photo) for photo in photos]


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    query = select(PhotoORM).filter_by(id=photo_id)\
        .options(selectinload(PhotoORM.comments), selectinload(PhotoORM.tags))
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return PhotoResponse.from_orm(db_photo)


@router.get("/{author_fullname}", response_model=List[PhotoResponse])
async def get_photos_by_author(author_username: str, db: AsyncSession = Depends(get_db)):
    query1 = select(UserORM).filter_by(username=author_username)
    result = await db.execute(query1)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Profile not found")
    query2 = select(ProfileORM).filter_by(user_id=user.id)
    result = await db.execute(query2)
    profile = result.scalars().first()
    query = select(PhotoORM).filter_by(author_fk=profile.id)\
        .options(selectinload(PhotoORM.comments), selectinload(PhotoORM.tags))
    result = await db.execute(query)
    photos = result.scalars().all()
    return [PhotoResponse.from_orm(photo) for photo in photos]


@router.put("/{photo_id}", response_model=PhotoResponse)
async def update_photo(db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserORM, Depends(auth_service.get_access_user)], photo_id: int, description: str = Form()):
    profile = await get_profile(user.id, db)
    query = select(PhotoORM).where(and_(PhotoORM.id == photo_id, PhotoORM.author_fk == profile.id))
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
    profile = await get_profile(user.id, db)
    query = select(PhotoORM).where(and_(PhotoORM.id == photo_id, PhotoORM.author_fk == profile.id))
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
