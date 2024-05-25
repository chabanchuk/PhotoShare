import asyncio
from datetime import datetime
from faker import Faker

from userprofile.orm import UserORM, ProfileORM
from database import get_db

fake = Faker()

async def create_fake_user_and_profile():
    async with get_db() as session:
        async with session.begin():
            for index in range(5):
                email = fake.email()
                username = fake.user_name()
                password = "password"
                registered_at = datetime.now()

                role = "admin" if index == 0 else "user"

                user = UserORM(
                    email=email,
                    username=username,
                    password=password,
                    registered_at=registered_at,
                    role=role
                )

                session.add(user)
                await session.flush()
                first_name = fake.first_name()
                last_name = fake.last_name()
                birthday = fake.date_of_birth(minimum_age=18, maximum_age=90)

                profile = ProfileORM(
                    first_name=first_name,
                    last_name=last_name,
                    full_name=f"{first_name} {last_name}",
                    birthday=birthday,
                    user_id=user.id
                )

                session.add(profile)

async def main():
    await create_fake_user_and_profile()

if __name__ == "__main__":
    asyncio.run(main())
