from datetime import datetime, timezone, timedelta
from typing import Any, TypeAlias, Literal, Annotated, List

from jose import jwt, JWTError
import bcrypt
from fastapi import security, Depends, HTTPException
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from userprofile.orm import UserORM, BlackListORM
from database import get_db
from settings import settings

Scope: TypeAlias = Literal["access_token", "refresh_token", "email_token"]


class Authentication:
    HASH_SERVICE = bcrypt
    ACCESS_ALGORITHM = settings.access_algorithm
    REFRESH_ALGORITHM = settings.refresh_algorithm
    SECRET_256 = settings.secret_256
    SECRET_512 = settings.secret_512
    REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_exp
    oauth2_schema = security.OAuth2PasswordBearer(tokenUrl="/auth/login")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify if the provided plain password matches the hashed password.

        Args:
            plain_password (str): The plain text password to be verified.
            hashed_password (str): The hashed password to be compared against.

        Returns:
            bool: True if the plain password matches the hashed password, False otherwise.
        """
        return self.HASH_SERVICE.checkpw(
            password=plain_password.encode(), hashed_password=hashed_password.encode()
        )

    def get_hash_password(self, plain_password: str) -> str:
        """
        Generates a hashed password from a plain text password using the bcrypt library.

        Args:
            plain_password (str): The plain text password to be hashed.

        Returns:
            str: The hashed password encoded as a string.
        """
        return self.HASH_SERVICE.hashpw(
            password=plain_password.encode(), salt=self.HASH_SERVICE.gensalt()
        ).decode()

    def create_token(self, email: str, scope: Scope, live_time: timedelta) -> str:
        """
        Creates a JWT token with the given email, scope, and live time.

        Args:
            email (str): The email associated with the token.
            scope (Scope): The scope of the token.
            live_time (timedelta): The duration the token is valid.

        Returns:
            str: The generated JWT token.

        Raises:
            None

        Algorithm:
            1. Get the current UTC time.
            2. Calculate the expiration time by adding the live time to the current time.
            3. Determine the key based on the scope.
            4. Determine the algorithm based on the scope.
            5. Create the payload dictionary with the email, current time, expiration time, and scope.
            6. Encode the payload into a JWT token using the key and algorithm.
            7. Return the generated JWT token.
        """
        current_time = datetime.now(timezone.utc)
        expiration_time = current_time + live_time

        key = (
            self.SECRET_256
            if scope in ["access_token", "email_token"]
            else self.SECRET_512
        )

        algorithm = (
            self.ACCESS_ALGORITHM
            if scope in ["access_token", "email_token"]
            else self.REFRESH_ALGORITHM
        )

        payload = {
            "sub": email,
            "iat": current_time,
            "exp": expiration_time,
            "scope": scope,
        }

        jwt_token = jwt.encode(claims=payload, key=key, algorithm=algorithm)

        return jwt_token

    def create_access_token(
        self, email: str, live_time: timedelta = timedelta(days=1)
    ) -> Any:
        """
        Creates an access token with the given email and optional live time.

        Args:
            email (str): The email associated with the access token.
            live_time (timedelta, optional): The duration the access token is valid. Defaults to 1 day.

        Returns:
            Any: The generated access token.
        """
        return self.create_token(email=email, live_time=live_time, scope="access_token")

    def create_refresh_token(
        self, email: str, live_time: timedelta = timedelta(days=7)
    ) -> Any:
        """
        Creates a refresh token with the given email and optional live time.

        Args:
            email (str): The email associated with the refresh token.
            live_time (timedelta, optional): The duration the refresh token is valid. Defaults to 7 days.

        Returns:
            Any: The generated refresh token.
        """
        return self.create_token(
            email=email, live_time=live_time, scope="refresh_token"
        )

    def create_email_token(
        self, email: str, live_time: timedelta = timedelta(hours=12)
    ) -> Any:
        """
        Creates an email token with the given email and optional live time.

        Args:
            email (str): The email associated with the email token.
            live_time (timedelta, optional): The duration the email token is valid. Defaults to 12 hours.

        Returns:
            Any: The generated email token.
        """
        return self.create_token(email=email, live_time=live_time, scope="email_token")

    async def get_user(
        self,
        token: Annotated[str, Depends(oauth2_schema)],
        db: Annotated[AsyncSession, Depends(get_db)],
        scope: Scope = "access_token",
    ) -> Any:
        """
        Retrieves the user associated with the given access token and database session.

        Args:
            token (str): The access token used for authentication.
            db (AsyncSession): The database session to retrieve the user from.
            scope (Scope, optional): The scope of the token. Defaults to "access_token".

        Returns:
            Any: The user associated with the access token.

        Raises:
            HTTPException: If the token is invalid, the token scope is invalid, the token is expired,
                or the user is not logged in.
        """
        key = (
            self.SECRET_256
            if scope in ["access_token", "email_token"]
            else self.SECRET_512
        )

        algorithm = (
            self.ACCESS_ALGORITHM
            if scope in ["access_token", "email_token"]
            else self.REFRESH_ALGORITHM
        )
        try:
            payload = jwt.decode(
                token=token,
                key=key,
                algorithms=[algorithm],
                options={"verify_exp": False},
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}"
            )

        if payload.get("scope") not in ["access_token", "refresh_token", "email_token"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope"
            )

        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        email = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Username not found in token",
            )

        user = await db.execute(select(UserORM).filter(UserORM.email == email))
        user = user.scalars().first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

        if all(
            [
                payload.get("scope") == "refresh_token",
                int(payload.get("exp"))
                <= int(datetime.timestamp(datetime.now(timezone.utc))),
            ]
        ):
            user.loggedin = False
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Use /auth/login to get new tokens",
            )

        if UserORM.loggedin:
            return user

        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not logged in. Use /auth/login",
        )

    async def get_access_user(
        self,
        token: Annotated[str, Depends(oauth2_schema)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> Any:
        """
        Retrieves the user associated with the given access token and database session.

        :param token: The access token used for authentication.
        :type token: str
        :param db: The database session to retrieve the user from.
        :type db: AsyncSession
        :return: The user associated with the access token.
        :rtype: Any
        """
        return await self.get_user(token=token, db=db, scope="access_token")

    async def get_refresh_user(
        self,
        token: Annotated[str, Depends(oauth2_schema)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> Any:
        """
        A function to get refresh user information based on the provided token and database session.

        Parameters:
            token (str): The token used to authenticate the user.
            db (AsyncSession): The database session to retrieve the user from.

        Returns:
            Any: The user retrieved using the token and database session with scope set to "refresh_token".
        """
        return await self.get_user(token=token, db=db, scope="refresh_token")

    async def get_email_user(
        self,
        token: Annotated[str, Depends(oauth2_schema)],
        db: Annotated[AsyncSession, Depends(get_db)],
    ) -> Any:
        """
        A function to retrieve the user information based on the access token and database session.

        Parameters:
            token (str): The access token required for authentication.
            db (AsyncSession): The database session.

        Returns:
            Any: The user information retrieved using the provided token and database session.
        """
        return await self.get_user(token=token, db=db, scope="email_token")

    def has_access_to_delete_tag(self, user: UserORM, tag_owner_id: int) -> bool:
        """
        Checks if the user has permission to delete the tag.

        Parameters:
            user (UserORM): The user who wants to remove the tag.
            tag_owner_id (int): ID of the user who owns the tag.

        Returns:
            bool: True if the user has access to remove the tag, False otherwise.
        """
        if user.role in ["moderator", "admin"]:
            return True
        return user.id == tag_owner_id

    async def add_to_blacklist(
        self,
        token: str,
        email: str,
        username: str,
        expires_delta: float,
        db: AsyncSession,
    ):
        """
        Adds a token to the blacklist.

        Args:
            token (str): The token to be added to the blacklist.
            email (str): The email associated with the token.
            username (str): The username associated with the token.
            expires_delta (float): The time in seconds until the token expires.
            db (AsyncSession): The database session.

        Returns:
            None

        Raises:
            None
        """
        payload = jwt.decode(token, self.SECRET_256, algorithms=[self.ACCESS_ALGORITHM])
        issued_at = datetime.utcfromtimestamp(payload["iat"])
        expire_access = datetime.utcnow() + timedelta(seconds=expires_delta)
        expire_refresh = issued_at + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

        blacklist = BlackListORM(
            email=email,
            username=username,
            token=token,
            expire_access=expire_access,
            expire_refresh=expire_refresh,
        )

        db.add(blacklist)
        await db.commit()

    async def is_blacklisted_token(self, token: str, db: AsyncSession) -> bool:
        """
        Check if a given token is blacklisted.

        Args:
            token (str): The token to check for blacklisting.
            db (AsyncSession): The database session.

        Returns:
            bool: True if the token is blacklisted, False otherwise.

        This function checks if a given token is present in the blacklist table. If the token is found, it checks if the
        expiration time of the token has passed. If the expiration time has passed, the token is deleted from the
        blacklist table and False is returned. If the token is still valid, True is returned. If the token is not found
        in the blacklist table, False is returned.
        """
        blacklist = await db.execute(
            select(BlackListORM).filter(BlackListORM.token == token)
        )
        blacklist = blacklist.scalars().first()

        if blacklist:
            if blacklist.expire_access < datetime.utcnow():
                await db.delete(blacklist)
                await db.commit()
                return False
            return True
        return False

    async def get_blacklisted_tokens(self, username: str, db: AsyncSession) -> List:
        """
        Retrieves a list of blacklisted tokens associated with a given username.

        Args:
            username (str): The username to retrieve blacklisted tokens for.
            db (AsyncSession): The database session.

        Returns:
            List: A list of blacklisted tokens associated with the given username.
        """
        blacklist_tokens = await db.execute(
            select(BlackListORM).filter(BlackListORM.username == username)
        )
        return blacklist_tokens.scalars().all()
