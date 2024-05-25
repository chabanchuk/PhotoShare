from typing import List
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from photo.orm import photo_tag_association_table
from database import Base


class TagORM(Base):
    __tablename__ = "tags"
    # columns
    id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # relations
    photos: Mapped[List["PhotoORM"]] = relationship(secondary=photo_tag_association_table, back_populates="tags")
