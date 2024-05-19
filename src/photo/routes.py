from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, APIRouter, status, Form
# from requests import HTTPError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import cloudinary
from cloudinary.uploader import upload, destroy
from starlette.responses import Response

from database import get_db
from photo.model import PhotoCreate, PhotoResponse, PhotoUpdate, PhotoModel, TransformRequest
from photo.orm import PhotoORM
from userprofile.orm import ProfileORM
from settings import settings


router = APIRouter(prefix='/photos', tags=["photos"])


cloudinary.config(
        cloud_name=settings.cloudinary_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )


@router.post("/", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def create_photo(description: str = Form(), file: UploadFile = File(), db: AsyncSession = Depends(get_db)):

    max_file_size = 3 * 1024 * 1024  # 3 megabytes
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > max_file_size:
        raise HTTPException(status_code=413, detail="File size exceeds the limit of 3 megabytes")
    await file.seek(0)
    cloudinary_result = upload(file.file, folder="photos/")
    photo = PhotoModel(description=description)
    db_photo = PhotoORM(url=cloudinary_result['secure_url'], public_id=cloudinary_result['public_id'],
            description=photo.description, author_fk=1)
    db.add(db_photo)
    await db.commit()
    await db.refresh(db_photo)
    return PhotoResponse.from_orm(db_photo)


@router.post("/transform", response_model=PhotoResponse, status_code=status.HTTP_200_OK)
async def transform_photo(
    photo_id: int = Form(...),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    crop: Optional[str] = Form(None),
    gravity: Optional[str] = Form(None),
    radius: Optional[str] = Form(None),
    effect: Optional[str] = Form(None),
    quality: Optional[str] = Form(None),
    format: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(PhotoORM).filter(PhotoORM.id == photo_id)
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    transformations = {key: value for key, value in locals().items() if key != 'db' and key != 'photo_id' and value is not None}
    try:
        transformed_url = upload(db_photo.url, **transformations)
        db_photo.url = transformed_url['secure_url']
        db.add(db_photo)
        await db.commit()
        await db.refresh(db_photo)
        return PhotoResponse.from_orm(db_photo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{photo_id}", response_model=PhotoResponse)
async def get_photo(photo_id: int, db: AsyncSession = Depends(get_db)):

    query = select(PhotoORM).filter_by(id=photo_id)
    result = await db.execute(query)
    db_photo = result.scalars().first()

    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return PhotoResponse.from_orm(db_photo)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    query = select(PhotoORM).filter_by(id=photo_id)
    result = await db.execute(query)
    photo = result.scalars().first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    destroy(photo.public_id)
    await db.delete(photo)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{photo_id}", response_model=PhotoResponse)
async def update_photo(photo_id: int, photo: PhotoUpdate, db: AsyncSession = Depends(get_db)):
    query = select(PhotoORM).filter_by(id=photo_id)
    result = await db.execute(query)
    db_photo = result.scalars().first()
    if not db_photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    db_photo.description = photo.description
    await db.commit()
    await db.refresh(db_photo)
    return PhotoResponse.from_orm(db_photo)
