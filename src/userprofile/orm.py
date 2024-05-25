from datetime import datetime, timezone, date
from typing import Optional, Any, List, TypeAlias, Literal

from sqlalchemy import String, Date, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from comment.orm import CommentORM
from database import Base, get_db
from photo.orm import PhotoORM

# Role typealias contains list of possible roles
Role: TypeAlias = Literal["user", "moderator", "admin"]


class UserORM(Base):
    """
    ORM mapping for UserAuth
    """

    __tablename__ = "users"

    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(80), unique=True)
    # username will be used to store email for OAuth2 compatibility
    username: Mapped[str] = mapped_column(unique=True)
    # password contains hashed password
    password: Mapped[str] = mapped_column(nullable=False)
    loggedin: Mapped[bool] = mapped_column(default=False)
    is_banned: Mapped[bool] = mapped_column(default=False)
    registered_at: Mapped[datetime] = mapped_column(default=datetime.now(timezone.utc))
    role: Mapped[Role] = mapped_column(String(20), default="user")
    # Relations
    profile: Mapped["ProfileORM"] = relationship(back_populates="user")


class ProfileORM(Base):
    """
    ORM mapping for ProfileData
    """

    __tablename__ = "profiles"
    # Table columns
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(20))
    last_name: Mapped[Optional[str]] = mapped_column(String(20))
    # full_name: Mapped[str] = mapped_column(String(),
    #                                        unique=True,
    #                                        default=full_name_calculated_default,
    #                                        onupdate=full_name_calculated_update)
    birthday: Mapped[Optional[date]] = mapped_column(Date())
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Realtions
    user: Mapped[UserORM] = relationship(back_populates="profile")
    photos: Mapped[List["PhotoORM"]] = relationship(back_populates="author")
    comments: Mapped[List["CommentORM"]] = relationship(back_populates="author")


class BlackListORM(Base):
    __tablename__ = "blacklist"
    # Columns
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]
    email: Mapped[str]
    token: Mapped[str] = mapped_column(unique=True)
    expire_access: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expire_refresh: Mapped[datetime] = mapped_column(DateTime(timezone=True))
