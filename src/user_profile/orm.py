from datetime import datetime, timezone, date
from typing import Optional, Any, List

from sqlalchemy import String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.comment.orm import CommentORM
from src.database import Base, get_db
from src.photo.orm import PhotoORM


async def full_name_calculated_default(context) -> str:
    """
    Calculates default (creation time) value for full_name field

    Arguments:
        context: current parameters for calling ORM

    Returns:
         str: strings with concatenated first and last name
    """
    first = await context.get_current_parameters().get('first_name')
    last = await context.get_current_parameters().get('last_name')
    last = f" {last}" if last is not None else ""
    return f"{first}{last}"


async def full_name_calculated_update(context) -> Any:
    """
    Calculates on_update event value for full_name field

    Arguments:
        context: current parameters for calling ORM

    Returns:
         str: strings with concatenated first and last name
    """
    first = await context.get_current_parameters().get('first_name')
    last = await context.get_current_parameters().get('last_name')
    id_ = await context.get_current_parameters().get('id_1')
    if id_ is None:
        return
    with get_db() as session:
        current = await session.get(ProfileORM, id_)
        first = first if first is not None else current.first_name
        last = last if last is not None else current.last_name
    last = f" {last}" if last is not None else ""
    return f"{first}{last}"


class UserORM(Base):
    """
    ORM mapping for UserAuth
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # username will be used to store email for OAuth2 compatibility
    email: Mapped[Optional[str | None]] = mapped_column(String(80),
                                                        unique=True)
    email_confirmed: Mapped[Optional[bool]] = mapped_column(default=False)
    username: Mapped[str] = mapped_column(unique=True)
    # password contains hashed password
    hashed_pwd: Mapped[str] = mapped_column(nullable=False)
    loggedin: Mapped[bool] = mapped_column(default=False)
    registered_at: Mapped[datetime] = mapped_column(
        default=datetime.now(timezone.utc)
    )
    profile: Mapped["ProfileORM"] = relationship(back_populates="user")


class ProfileORM(Base):
    """
    ORM mapping for ProfileData
    """
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(20))
    last_name: Mapped[Optional[str]] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(),
                                           unique=True,
                                           default=full_name_calculated_default,
                                           onupdate=full_name_calculated_update)
    email: Mapped[Optional[str]] = mapped_column(String(80),
                                                 unique=True)
    birthday: Mapped[Optional[date]] = mapped_column(Date())
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[UserORM] = relationship(back_populates='profile')
    photos: Mapped[List["PhotoORM"]] = relationship(back_populates='owner')
    comment: Mapped[List["CommentORM"]] = relationship(back_populates="author")
