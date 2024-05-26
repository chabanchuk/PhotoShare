import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from auth.service import Authentication
from auth.require_role import require_role
from userprofile.orm import UserORM

auth = Authentication()


@pytest.fixture
def client():
    """
    Creates and returns a FastAPI client for testing purposes.

    Returns:
        TestClient: A test client for the FastAPI application.
    """
    from fastapi import FastAPI
    app = FastAPI()
    client = TestClient(app)
    return client


@pytest.fixture
def create_user():
    """
    This function is a pytest fixture that creates a user with the given role.

    Parameters:
        role (str): The role of the user.

    Returns:
        UserORM: An instance of the UserORM class representing the created user.
    """
    def _create_user(role):
        return UserORM(id=1, email="test@example.com", role=role)

    return _create_user


@pytest.mark.asyncio
async def test_require_role_allowed_role(create_user):
    """
    Test case to verify that the `require_role` dependency function correctly allows access for users with the "admin" role.

    This test case creates a user with the "admin" role using the `create_user` fixture. It then calls the `require_role` function with the allowed roles ["admin"] and passes the user as the dependency. The result of the dependency function is asserted to be equal to the user object.

    Parameters:
        create_user (Callable): A fixture function that creates a user object with the specified role.

    Returns:
        None
    """
    user = create_user("admin")

    dependency = require_role(["admin"])
    result = await dependency(user)

    assert result == user


@pytest.mark.asyncio
async def test_require_role_disallowed_role(create_user):
    """
    Test case to verify that the `require_role` dependency function correctly raises an HTTPException with a status code of 403 and the detail message "Granted role has insufficient permissions." when a user with a disallowed role is passed as a dependency.

    This test case creates a user with the "user" role using the `create_user` fixture. It then calls the `require_role` function with the allowed roles ["admin"] and passes the user as the dependency. The test expects the `require_role` function to raise an HTTPException with a status code of 403 and the detail message "Granted role has insufficient permissions."

    Parameters:
        create_user (Callable): A fixture function that creates a user object with the specified role.

    Returns:
        None
    """
    user = create_user("user")

    dependency = require_role(["admin"])

    with pytest.raises(HTTPException) as exc_info:
        await dependency(user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "Granted role has insufficient permissions."
