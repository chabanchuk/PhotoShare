from fastapi import FastAPI
import uvicorn

from auth.routes import router as auth_router
from comment.routes import router as comment_router
from photo.routes import router as photo_router
from user_profile.routes import router as user_router
from frontend.routes import router as frontend_router

from database import engine
from user_profile.model import Base

app = FastAPI()

@app.on_event("startup")
async def startup():
    """
    Подія запуску для створення таблиць в базі даних.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown():
    """
    Подія завершення роботи додатку для закриття з'єднання з базою даних.
    """
    await engine.dispose()

app.include_router(auth_router)
app.include_router(comment_router)
app.include_router(photo_router)
app.include_router(user_router)
app.include_router(frontend_router)


if __name__ == "__main__":
    uvicorn.run(app=app,
                host="localhost",
                port=8080)
