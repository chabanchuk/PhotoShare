from datetime import datetime, timezone, timedelta
from typing import Any, TypeAlias, Literal, Annotated

from jose import jwt, JWTError
import bcrypt
from fastapi import security, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from starlette import status

from user_profile.orm import UserORM
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
        Verify the provided plain password against the hashed password.

        Args:
            plain_password (str): The plain text password to be verified.
            hashed_password (str): The hashed password for comparison.

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
        Hashes the provided plain password using the HASH_SERVICE, encoding the password and generating a salt.

        Args:
            plain_password (str): The plain text password to be hashed.

        Returns:
            str: The hashed password as a string.
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
        A function to create a token based on the provided email, scope, and live time.

        Parameters:
            email (str): The email for which the token is created.
            scope (Scope): The scope of the token.
            live_time (timedelta): The duration of time the token will be valid.

        Returns:
            str: The generated JWT token.
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
        Creates an access token for the given email with an optional custom live time.

        Parameters:
            email (str): The email for which the access token is being created.
            live_time (timedelta, optional): The duration for which the token will be valid. Defaults to 1 day.

        Returns:
            str: The access token generated.
        """
        return self.create_token(self,
                                 email=email,
                                 live_time=live_time,
                                 scope="access_token")

    def create_refresh_token(
            self,
            email: str,
            live_time: timedelta = timedelta(days=7)
    ) -> str:
        """
        A function that creates a refresh token for a given email with an optional live time.

        Parameters:
            email (str): The email for which the refresh token is created.
            live_time (timedelta, optional): The live time of the token (default is 7 days).

        Returns:
            str: The refresh token created.
        """
        return self.create_token(self,
                                 email=email,
                                 scope="refresh_token",
                                 live_time=live_time)

    def create_email_token(
            self,
            email: str,
            live_time: timedelta = timedelta(hours=12)
    ) -> str:
        """
        Create an email token for the given email address with an optional expiration time.

        Parameters:
            email (str): The email address for which the token is created.
            live_time (timedelta, optional): The expiration time for the token (default is 12 hours).

        Returns:
            str: The generated email token.
        """
        return self.create_token(self,
                                 email=email,
                                 live_time=live_time,
                                 scope="email_token")

    def get_user(
            self,
            token: Annotated[str, Depends(oauth2_schema)],
            db: Annotated[AsyncSession, Depends(get_db)],
            scope: Scope = "access_token"
    ) -> Any:
        """
        A function to get user information based on the provided token and scope.
        Parameters:
            token: A string token annotated with oauth2_schema.
            db: A Session annotated with get_db function.
            scope: Optional parameter indicating the scope of the token, defaults to "access_token".
        Returns:
            Any: Returns the user information if valid, else raises appropriate HTTPExceptions.
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

        user = db.query(UserORM).filter(
            UserORM.email == email
        ).first()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        if all([payload.get("scope") == "refresh_token",
                int(payload.get("exp"))
                <= int(datetime.timestamp(datetime.now(timezone.utc)))]):
            user.loggedin = False
            db.commit()
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

    def get_access_user(
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
            db=db
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

    def get_email_user(
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
