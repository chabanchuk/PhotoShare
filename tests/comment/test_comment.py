import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from auth.service import auth as auth_service
from comment.model import CommentCreate, CommentUpdate
from comment.routes import router
from main import app


@pytest.fixture(scope='module')
def client(session):
    """
    The client function is a fixture that will be called once per test function.
    It returns a TestClient instance, which provides an API to make HTTP requests
    to the application being tested. The client fixture also ensures that the 
    application context is pushed before each test and popped after each test.
    
    :param session: Pass the database session to the test client
    :return: A testclient, which is a class from starlette
    """
    app.include_router(router)
    return TestClient(app)

@pytest.fixture
def headers(get_access_token):
    return {"Authorization": f"Bearer {get_access_token}"}


def test_read_comments(client, session):
    """
    The test_read_comments function tests the read comments endpoint.
    It does this by making a GET request to /comments/ and asserting that the response is 200 OK,
    and that it returns a list of comments.
    
    :param client: Make requests to the server
    :param session: Create a database session
    :return: A list of comments
    """
    response = client.get("/comments/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_comment(client, session):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних є коментар з id=1
    """
    The test_get_comment function tests the GET /comments/<id> endpoint.
    It does so by making a request to the server and checking that:
    - The response status code is 200 (OK)
    - The response data is valid JSON
    
    :param client: Make requests to the application
    :param session: Create a database session for the test
    :return: A comment with the id=1
    """
    response = client.get("/comments/1")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_create_comment(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних є фото з id=1
    """
    The test_create_comment function tests the creation of a comment.
    It does so by sending a POST request to the /comments/<photo_id> endpoint with an access token and JSON data containing 
    the text of the comment. The test asserts that:
        1) The response status code is 201 (Created). This means that the server successfully created a new resource. 
        2) The response body contains JSON data.
    
    :param client: Make requests to the api
    :param session: Create a database session for the test
    :param user: Create a user in the database before running the test
    :param headers: Authorization headers with access token
    :return: A 201 status code
    """
    response = client.post("/comments/1", headers=headers, json={"text": "Test comment"})
    assert response.status_code == 201
    assert isinstance(response.json(), dict)


def test_create_comment_no_photo(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних немає фото з id=999
    """
    The test_create_comment_no_photo function tests the creation of a comment for a non-existing photo.
    It expects a 404 response code.
    
    :param client: Make requests to the api
    :param session: Create a database session for the test
    :param user: Create a comment for the photo with id=999
    :param headers: Authorization headers with access token
    :return: 404
    """
    response = client.post("/comments/999", headers=headers, json={"text": "Test comment"})
    assert response.status_code == 404


def test_create_comment_author_photo(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних є фото з id=2, яке належить користувачу
    """
    The test_create_comment_author_photo function tests that a user cannot create a comment on their own photo.
    It expects a 405 response code.
    
    :param client: Make requests to the application
    :param session: Create a database session for the test
    :param user: Create a user in the database before running the test
    :param headers: Authorization headers with access token
    :return: 405 because the method is not allowed
    """
    response = client.post("/comments/2", headers=headers, json={"text": "Test comment"})
    assert response.status_code == 405


def test_update_comment(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних є коментар з id=1
    """
    The test_update_comment function tests the update_comment endpoint.
    It expects a 200 response code and a valid JSON object.
    
    :param client: Make requests to the api
    :param session: Create a database session for the test
    :param user: Create a user in the database before running the test
    :param headers: Authorization headers with access token
    :return: A response with a 200 status code and the updated comment object in JSON format
    """
    response = client.patch("/comments/1", headers=headers, json={"text": "Updated comment"})
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_update_comment_no_comment(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних немає коментаря з id=999
    """
    The test_update_comment_no_comment function tests the update_comment endpoint for a non-existing comment.
    It expects a 404 response code.
    
    :param client: Make requests to the api
    :param session: Create a database session for the test
    :param user: Create a new user in the database
    :param headers: Authorization headers with access token
    :return: 404
    """
    response = client.patch("/comments/999", headers=headers, json={"text": "Updated comment"})
    assert response.status_code == 404


def test_update_comment_not_author(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних є коментар з id=2, який належить іншому користувачу
    """
    The test_update_comment_not_author function tests that a user cannot update a comment they do not own.
    It expects a 403 response code.
    
    :param client: Make requests to the application
    :param session: Create a database session for the test
    :param user: Create a user in the database
    :param headers: Authorization headers with access token
    :return: 403 status code
    """
    response = client.patch("/comments/2", headers=headers, json={"text": "Updated comment"})
    assert response.status_code == 403


def test_delete_comment(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних є коментар з id=1
    """
    The test_delete_comment function tests the DELETE /comments/delete/<int:comment_id> endpoint.
    It expects a 200 response code.
    
    :param client: Make requests to the api
    :param session: Create a database session for the test
    :param user: Create a user in the database before running the test
    :param headers: Authorization headers with access token
    :return: 200
    """
    response = client.delete("/comments/delete/1", headers=headers)
    assert response.status_code == 200


def test_delete_comment_no_comment(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних немає коментаря з id=999
    """
    The test_delete_comment_no_comment function tests the delete_comment endpoint for a non-existing comment.
    It expects a 404 response code.
    
    :param client: Make requests to the api
    :param session: Create a database session for the test
    :param user: Create a user in the database before running this test
    :param headers: Authorization headers with access token
    :return: 404
    """
    response = client.delete("/comments/delete/999", headers=headers)
    assert response.status_code == 404


def test_delete_comment_not_moderator(client, session, user, headers):
    # Перед виконанням цього тесту, переконайтеся, що в базі даних є коментар з id=2, і користувач не є модератором або адміністратором
    """
    The test_delete_comment_not_moderator function tests that a non-moderator cannot delete another user's comment.
    It expects a 403 response code.
    
    :param client: Make requests to the application
    :param session: Access the database
    :param user: Create a user in the database before running the test
    :param headers: Authorization headers with access token
    :return: 403
    """
    response = client.delete("/comments/delete/2", headers=headers)
    assert response.status_code == 403