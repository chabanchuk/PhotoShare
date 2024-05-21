from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from faker import Faker
from passlib.context import CryptContext
from datetime import datetime
import random

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    photos = relationship("Photo", back_populates="owner")

class Photo(Base):
    __tablename__ = "photos"
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, index=True)
    description = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="photos")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    tags = Column(String)  

Base.metadata.create_all(bind=engine)

app = FastAPI()

fake = Faker()

def get_password_hash(password):
    return pwd_context.hash(password)

def create_fake_users(db):
    roles = ["user", "moderator", "admin"]
    users = []
    for _ in range(5):
        role = roles[0] if len(users) == 0 else random.choice(roles)  
        user = User(
            username=fake.user_name(),
            email=fake.email(),
            hashed_password=get_password_hash("password"),
            full_name=fake.name(),
            role=role,
            is_active=True,
        )
        db.add(user)
        users.append(user)
    db.commit()
    return users

@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    users = create_fake_users(db)
    for user in users:
        print(f"Created user: {user.username}, role: {user.role}")
    db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
