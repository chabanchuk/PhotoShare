from datetime import datetime, timedelta


from jose.jwt import decode
from auth.service import Authentication


auth = Authentication()


def test_password_hashing():
    """
    Test the password hashing functionality of the authentication service.

    This function tests the password hashing functionality by generating a plain text password,
    hashing it using the `get_hash_password` method of the authentication service, and then
    verifying the hashed password using the `verify_password` method.

    Parameters:
        None

    Returns:
        None

    Raises:
        AssertionError: If the plain text password is not successfully verified against the
        hashed password.

    """
    plain_password = "password123"
    hashed_password = auth.get_hash_password(plain_password)
    assert auth.verify_password(plain_password, hashed_password)


def test_verify_password():
    """
    Test the verify_password function of the Authentication class.

    This function tests the verify_password function by generating a plain text password and a hashed password
    using the get_hash_password method of the Authentication class. It then verifies if the plain text password
    matches the hashed password using the verify_password method. The function asserts that the result is True
    when the plain text password is correct and False when the plain text password is incorrect.

    Parameters:
        None

    Returns:
        None

    Raises:
        AssertionError: If the result of the verify_password method is not as expected.
    """
    plain_password = "password123"
    hashed_password = auth.get_hash_password(plain_password)
    assert auth.verify_password(plain_password, hashed_password) == True

    wrong_password = "wrongpassword"
    assert auth.verify_password(wrong_password, hashed_password) == False


def test_create_token():
    """
    Test the create_token function in the auth module.

    This function tests the create_token function by generating a token with a given email, scope, and live time.
    It then decodes the token using the SECRET_256 secret and the ACCESS_ALGORITHM algorithm.
    The function asserts that the decoded token contains the correct email, scope, and that the issued at time
    (iat) is less than or equal to the current time. It also asserts that the expiration time is greater than or
    equal to the expected expiration time, which is calculated by adding the live time to the current time.

    Parameters:
        None

    Returns:
        None

    Raises:
        AssertionError: If the decoded token does not contain the correct email, scope, or if the issued at time
                        is greater than the current time or if the expiration time is less than the expected
                        expiration time.
    """
    email = "test@example.com"
    scope = "access_token"
    live_time = timedelta(minutes=30)

    token = auth.create_token(email, scope, live_time)

    decoded_token = decode(token, auth.SECRET_256, algorithms=[auth.ACCESS_ALGORITHM])

    assert decoded_token["sub"] == email
    assert decoded_token["scope"] == scope

    current_time = datetime.now()
    assert decoded_token["iat"] <= current_time.timestamp()

    expiration_time = datetime.fromtimestamp(decoded_token["exp"])
    expiration_time = expiration_time.replace(microsecond=0)
    expected_expiration_time = (current_time + live_time).replace(microsecond=0)
    assert expiration_time >= expected_expiration_time


def test_create_access_token():
    """
    Test the create_access_token function in the auth module.

    This function tests the create_access_token function by generating an access token with a given email and live time.
    It then decodes the token using the SECRET_256 secret and the ACCESS_ALGORITHM algorithm.
    The function asserts that the decoded token contains the correct email and scope.
    It also asserts that the issued at time (iat) is less than or equal to the current time.
    It checks that the expiration time is greater than or equal to the expected expiration time,
    which is calculated by adding the live time to the current time.

    Parameters:
        None

    Returns:
        None

    Raises:
        AssertionError: If the decoded token does not contain the correct email, scope, or if the issued at time
                        is greater than the current time or if the expiration time is less than the expected
                        expiration time.
    """
    email = "test@example.com"
    live_time = timedelta(minutes=0)

    token = auth.create_access_token(email, live_time)

    decoded_token = decode(token, auth.SECRET_256, algorithms=[auth.ACCESS_ALGORITHM])

    assert decoded_token["sub"] == email
    assert decoded_token["scope"] == "access_token"

    current_time = datetime.now()
    assert decoded_token["iat"] <= current_time.timestamp()
    assert decoded_token["exp"] >= current_time.timestamp() + live_time.total_seconds() - 1


def test_create_refresh_token():
    """
    Test the create_refresh_token function in the auth module.

    This function tests the create_refresh_token function by generating a refresh token with a given email and live time.
    It then decodes the token using the SECRET_512 secret and the REFRESH_ALGORITHM algorithm.
    The function asserts that the decoded token contains the correct email and scope.
    It also asserts that the issued at time (iat) is less than or equal to the current time.
    It checks that the expiration time is greater than or equal to the expected expiration time,
    which is calculated by adding the live time to the current time.

    Parameters:
        None

    Returns:
        None

    Raises:
        AssertionError: If the decoded token does not contain the correct email, scope, or if the issued at time
                        is greater than the current time or if the expiration time is less than the expected
                        expiration time.
    """
    email = "test@example.com"
    live_time = timedelta(days=7)

    token = auth.create_refresh_token(email, live_time)

    decoded_token = decode(token, auth.SECRET_512, algorithms=[auth.REFRESH_ALGORITHM])

    assert decoded_token["sub"] == email
    assert decoded_token["scope"] == "refresh_token"

    current_time = datetime.now()
    assert decoded_token["iat"] <= current_time.timestamp()
    assert decoded_token["exp"] >= current_time.timestamp() + live_time.total_seconds() - 1


def test_create_email_token():
    """
    Test the create_email_token function in the auth module.

    This function tests the create_email_token function by generating an email token with a given email and live time.
    It then decodes the token using the SECRET_256 secret and the ACCESS_ALGORITHM algorithm.
    The function asserts that the decoded token contains the correct email and scope.
    It also asserts that the issued at time (iat) is less than or equal to the current time.
    It checks that the expiration time is greater than or equal to the expected expiration time,
    which is calculated by adding the live time to the current time.

    Parameters:
        None

    Returns:
        None

    Raises:
        AssertionError: If the decoded token does not contain the correct email, scope, or if the issued at time
                        is greater than the current time or if the expiration time is less than the expected
                        expiration time.
    """
    email = "test@example.com"
    live_time = timedelta(hours=12)

    token = auth.create_email_token(email, live_time)

    decoded_token = decode(token, auth.SECRET_256, algorithms=[auth.ACCESS_ALGORITHM])

    assert decoded_token["sub"] == email
    assert decoded_token["scope"] == "email_token"

    current_time = datetime.now()
    assert decoded_token["iat"] <= current_time.timestamp()
    assert decoded_token["exp"] >= current_time.timestamp() + live_time.total_seconds() - 1


