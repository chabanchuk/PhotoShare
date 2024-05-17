from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TagORM(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    tag = Column(String, unique=True, index=True)
