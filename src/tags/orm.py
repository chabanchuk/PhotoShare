from sqlalchemy import String, Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from photo import photo_tag_association_table

class TagORM(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    # We can set up a lot of links with photos through the association table
    photos = relationship("PhotoORM", secondary=photo_tag_association_table, back_populates="tags")