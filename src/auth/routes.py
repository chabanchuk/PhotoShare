from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.hash import bcrypt

from database.models import User
from database.db import get_db

router = APIRouter()

@router.post("/users/", response_model=User)
async def create_user(username: str, password: str, db: AsyncSession = Depends(get_db)):
    """
    Створити нового користувача.

    Args:
        username (str): Ім'я користувача.
        password (str): Пароль користувача.
        db (AsyncSession, optional): Сеанс бази даних. За замовчуванням використовує Depends(get_db).

    Returns:
        User: Створений користувач.
    """
    hashed_password = bcrypt.hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
