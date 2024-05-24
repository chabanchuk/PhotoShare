import asyncio
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from userprofile.orm import UserORM, ProfileORM
from database import get_db, Base  

fake = Faker()

DATABASE_URL = ""  

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

async def create_fake_user_and_profile(session):
    async with session() as db:
        async with db.begin():
            for _ in range(5):
                email = fake.email()
                username = fake.user_name()
                password = fake.password()
                registered_at = datetime.now(fake.timezone())

                user = UserORM(
                    email=email,
                    username=username,
                    password=password,
                    registered_at=registered_at,
                    role="user"
                )

                db.add(user)
                await db.flush()  
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

                db.add(profile)

        await db.commit()

async def main():
    async with async_session() as session:
        await create_fake_user_and_profile(session)

if __name__ == "__main__":
    asyncio.run(main())


