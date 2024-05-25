from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from main import app

from database import Base, get_db
from auth.service import Authentication
import logging


auth_service = Authentication()

logging.basicConfig(filename='debug.log', level=logging.DEBUG)


# SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.sqlite"

engine = create_engine(SQLALCHEMY_DATABASE_URL,
                       connect_args={"check_same_thread": False},
                       poolclass=StaticPool)

TestingSession = sessionmaker(autocommit=False,
                              autoflush=False,
                              bind=engine)


@pytest.fixture(scope='module')
def session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logging.info(f"Database tables: {Base.metadata.tables}")
    db = TestingSession()
    try:
        logging.debug(f"session yield: {db}")
        yield db
    finally:
        logging.debug(f"session close: {db}")
        db.close()


@pytest.fixture(scope='module')
def client(session):
    # Dependency override
    def override_get_db():
        try:
            logging.debug(f"session yield: {session}")
            yield session
        except Exception as e:
            logging.error(f"session error: {e}")
        finally:
            logging.debug(f"session close: {session}")
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture(scope='module')
def user():
    return {
        "fullname": "Luk Skywoker",
        "email": "djedai@tatuin.emp",
        "hashed_pwd": "May_the_4th",
        "id": 1,
        "loggedin": True,
        "email_confirmed": True,
        "avatar_url": "cloudinary_url"
    }


@pytest.fixture(scope='module')
def get_access_token():
    return auth_service.create_access_token(
        auth_service,
        email="djedai@tatuin.emp"
    )
