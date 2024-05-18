from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from passlib.hash import bcrypt
#
# from user_profile.model import User
# from database import get_db
#
router = APIRouter()
#
# @router.post("/users/", response_model=User)
# async def create_user(username: str, password: str, db: AsyncSession = Depends(get_db)):
#     """
#     Create a new user.
#
#     Args:
#         username (str): User name.
#         password (str): User password.
#         db (AsyncSession, optional): Database session. By default, it uses Depends(get_db).
#
#     Returns:
#         User: User created.
#     """
#     # We convert the password string into bytes before hashing
#     hashed_password_bytes = bcrypt.hash(password.encode())
#     # Return the bytes to the string after hashing
#     hashed_password = hashed_password_bytes.decode()
#     new_user = User(username=username, hashed_password=hashed_password)
#     db.add(new_user)
#     await db.commit()
#     await db.refresh(new_user)
#     return new_user
