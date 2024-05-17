from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.sql import func
from sqlalchemy import String, Integer, DateTime
from src.database import Base
from src.user_profile.orm import ProfileORM
from typing import List, Optional
from src.comment.orm import CommentORM


class PhotoORM(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    author_name: Mapped[str] = mapped_column(ForeignKey("profiles.full_name", ondelete="CASCADE"))
    author: Mapped[ProfileORM] = relationship("ProfileORMr", back_populates="photos")
    comments: Mapped[List["CommentORM"]] = relationship(back_populates="photos")
    tags: Mapped[List["TagORM"]] = relationship(back_populates="photos")

