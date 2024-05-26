from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from main import app

from database import Base, get_db
from auth.service import auth as auth_service
import logging


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
        yield db
    finally:
        db.close()


@pytest.fixture(scope='module')
def client(session):
    # Dependency override
    def override_get_db():
        try:
            yield session
        except Exception as e:
            logging.error(f"session error: {e}")
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture(scope='module')
def user_admin():
    return {
        "username": "duke_nukem",
        "email": "djedai@tatuin.emp",
        "password": "May_the_4th",
        "id": 1,
        "loggedin": True,
        "is_banned": False,
        "role": "admin"
    }


@pytest.fixture(scope='module')
def user_moder():
    return {
        "username": "vlad_dracula",
        "email": "blood@transilvania.tasty",
        "password": "light_is_boo",
        "id": 2,
        "loggedin": True,
        "is_banned": False,
        "role": "moderator"
    }


@pytest.fixture(scope='module')
def user():
    return {
        "username": "pes_patron",
        "email": "havhav@town.in",
        "password": "meat_n_bones",
        "id": 3,
        "loggedin": True,
        "is_banned": False,
        "role": "user"
    }


@pytest.fixture(scope='module')
def get_access_token():
    iat = datetime.now(timezone.utc)
    return auth_service.create_access_token(
        sub="djedai@tatuin.emp",
        iat=iat
    )
