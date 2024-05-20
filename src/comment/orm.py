from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database import Base


class CommentORM(Base):
    """
    ORM mapping for Comment
    """
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    author_fk: Mapped[int] = mapped_column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'))
    photo_fk: Mapped[int] = mapped_column(Integer, ForeignKey('photos.id', ondelete='CASCADE'))

    author: Mapped["ProfileORM"] = relationship("ProfileORM", back_populates="comments", cascade="all, delete")
    photo: Mapped["PhotoORM"] = relationship("PhotoORM", back_populates="comments", cascade="all, delete")
