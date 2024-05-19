from datetime import datetime, timezone, timedelta
from typing import Any, TypeAlias, Literal, Annotated

from jose import jwt, JWTError
import bcrypt
from fastapi import security, Depends, HTTPException
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from userprofile.orm import UserORM
from database import get_db
from settings import settings

Scope: TypeAlias = Literal['access_token', 'refresh_token', 'email_token']


class Authentication:
    HASH_SERVICE = bcrypt
    ACCESS_ALGORITHM = settings.access_algorithm
    REFRESH_ALGORITHM = settings.refresh_algorithm
    SECRET_256 = settings.secret_256
    SECRET_512 = settings.secret_512
    oauth2_schema = security.OAuth2PasswordBearer(tokenUrl="/auth/login")

    def verify_password(
            self,
            plain_password: str,
            hashed_password: str
    ) -> bool:
        """
        Verify if the given plain password matches the hashed password.

        Args:
            plain_password (str): The plain text password to be verified.
            hashed_password (str): The hashed password to compare against.

        Returns:
            bool: True if the plain password matches the hashed password, False otherwise.
        """
        return self.HASH_SERVICE.checkpw(
            password=plain_password.encode(),
            hashed_password=hashed_password.encode()
        )

    def get_hash_password(
            self,
            plain_password: str
    ) -> str:
        """
        Generates a hashed password from a plain text password using the bcrypt library.

        Args:
            plain_password (str): The plain text password to be hashed.

        Returns:
            str: The hashed password encoded as a string.
        """
        return self.HASH_SERVICE.hashpw(
            password=plain_password.encode(),
            salt=self.HASH_SERVICE.gensalt()
        ).decode()

    def create_token(
            self,
            email: str,
            scope: Scope,
            live_time: timedelta
    ) -> str:
        """
        Creates a JWT token with the given email, scope, and live time.

        Parameters:
            email (str): The email associated with the token.
            scope (Scope): The scope of the token.
            live_time (timedelta): The duration for which the token is valid.

        Returns:
            str: The generated JWT token.

        Algorithm:
            1. Get the current time in UTC.
            2. Calculate the expiration time by adding the live time to the current time.
            3. Determine the key and algorithm based on the scope:
                - If the scope is "access_token" or "email_token", use the SECRET_256 key and ACCESS_ALGORITHM
                algorithm.
                - Otherwise, use the SECRET_512 key and REFRESH_ALGORITHM algorithm.
            4. Create the payload with the email, expiration time, and scope.
            5. Encode the payload using the selected key and algorithm to generate the JWT token.
            6. Return the generated JWT token.
        """
        current_time = datetime.now(timezone.utc)
        expiration_time = current_time + live_time

        key = self.SECRET_256 \
            if scope == "access_token" or scope == "email_token" \
            else self.SECRET_512

        algorithm = self.ACCESS_ALGORITHM \
            if scope == "access_token" \
            else self.REFRESH_ALGORITHM

        payload = {
            "sub": email,
            "exp": expiration_time,
            "scope": scope
        }

        jwt_token = jwt.encode(claims=payload,
                               key=key,
                               algorithm=algorithm)

        return jwt_token

    def create_access_token(
            self,
            email: str,
            live_time: timedelta = timedelta(days=1)
    ) -> str:
        """
        Creates an access token for the given email with an optional live time.

        Parameters:
            email (str): The email for which the access token is created.
            live_time (timedelta, optional): The live time of the token (default is 1 day).

        Returns:
            str: The access token created.

        This function calls the `create_token` method with the provided email, live time, and scope "access_token"
        to generate an access token.
        """
        return self.create_token(email=email,
                                 live_time=live_time,
                                 scope="access_token")

    def create_refresh_token(
            self,
            email: str,
            live_time: timedelta = timedelta(days=7)
    ) -> str:
        """
        Creates a refresh token for the given email with an optional live time.

        Parameters:
            email (str): The email for which the refresh token is created.
            live_time (timedelta, optional): The live time of the token (default is 7 days).

        Returns:
            str: The refresh token created.

        This function calls the `create_token` method with the provided email, scope "refresh_token", and live
        time to generate a refresh token.
        """
        return self.create_token(email=email,
                                 scope="refresh_token",
                                 live_time=live_time)

    def create_email_token(
            self,
            email: str,
            live_time: timedelta = timedelta(hours=12)
    ) -> str:
        """
        Creates an email token for the given email with an optional live time.

        Parameters:
            email (str): The email for which the email token is created.
            live_time (timedelta, optional): The live time of the token (default is 12 hours).

        Returns:
            str: The email token created.

        This function calls the `create_token` method with the provided email, live time, and scope "email_token"
        to generate an email token.
        """
        return self.create_token(email=email,
                                 live_time=live_time,
                                 scope="email_token")

    async def get_user(
            self,
            token: Annotated[str, Depends(oauth2_schema)],
            db: Annotated[AsyncSession, Depends(get_db)],
            scope: Scope = "access_token"
    ) -> Any:
        """
        Retrieves a user from the database based on the provided token and scope.

        Parameters:
            token (Annotated[str, Depends(oauth2_schema)]): The token used for authentication.
            db (Annotated[AsyncSession, Depends(get_db)]): The database session.
            scope (Scope, optional): The scope of the token (default is "access_token").

        Returns:
            Any: The user object retrieved from the database.

        Raises:
            HTTPException: If the token is invalid, the token scope is invalid, the user is not found,
                            or the token has expired.

        This function decodes the token using the provided key and algorithm. It then checks the token
        scope and expiration time. If the token is valid, it retrieves the user from the database
        based on the email in the token payload. If the user is not found, it raises an HTTPException
        with a status code of 404. If the token scope is "refresh_token" and it has expired, it sets
        the user's "loggedin" attribute to False in the database and raises an HTTPException with a
        status code of 401. If the user is logged in, it returns the user object; otherwise, it raises
        an HTTPException with a status code of 401.
        """
        key = self.SECRET_256 \
            if scope == "access_token" or scope == "email_token" \
            else self.SECRET_512

        algorithm = self.ACCESS_ALGORITHM \
            if scope == "access_token" or scope == "email_token" \
            else self.REFRESH_ALGORITHM

        try:
            payload = jwt.decode(token=token,
                                 key=key,
                                 algorithms=[algorithm],
                                 options={"verify_exp": False})
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}"
            )

        if payload.get("scope") not in ["access_token", "refresh_token"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token scope"
            )

        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        if all([payload.get("scope") == "access_token",
                int(payload.get("exp"))
                <= int(datetime.timestamp(datetime.now(timezone.utc)))]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Use /auth/refresh with refresh token"
            )

        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token scope"
            )

        user = await db.execute(select(UserORM).filter(UserORM.email == email)).scalars().first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        if all([payload.get("scope") == "refresh_token",
                int(payload.get("exp"))
                <= int(datetime.timestamp(datetime.now(timezone.utc)))]):
            user.loggedin = False
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Use /auth/login to get new tokens"
            )

        if UserORM.loggedin:
            return user

        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not logged in. Use /auth/login"
        )

    async def get_access_user(
            self,
            token: Annotated[str, Depends(oauth2_schema)],
            db: Annotated[AsyncSession, Depends(get_db)]
    ) -> Any:
        """
        A function to get access to a user with the provided token and database session.

        Parameters:
            token (str): The token used to authenticate the user.
            db (AsyncSession): The database session to retrieve the user from.

        Returns:
            Any: The user retrieved using the token and database session.
        """
        return self.get_user(
            token=token,
            db=db,
            scope="access_token"
        )

    async def get_refresh_user(
            self,
            token: Annotated[str, Depends(oauth2_schema)],
            db: Annotated[AsyncSession, Depends(get_db)]
    ) -> Any:
        """
        A function to get refresh user information based on the provided token and database session.

        Parameters:
            token (str): The token used to authenticate the user.
            db (AsyncSession): The database session to retrieve the user from.

        Returns:
            Any: The user retrieved using the token and database session with scope set to "refresh_token".
        """
        return self.get_user(
            token=token,
            db=db,
            scope="refresh_token"
        )

    async def get_email_user(
            self,
            token: Annotated[str, Depends(oauth2_schema)],
            db: Annotated[AsyncSession, Depends(get_db)]
    ) -> Any:
        """
        A function to retrieve the user information based on the access token and database session.

        Parameters:
            token (str): The access token required for authentication.
            db (AsyncSession): The database session.

        Returns:
            Any: The user information retrieved using the provided token and database session.
        """
        return self.get_user(
            token=token,
            db=db,
            scope="email_token"
        )


if __name__ == "__main__":
    auth_service = Authentication()
    print(auth_service.get_hash_password("password"))
