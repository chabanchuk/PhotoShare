from fastapi import FastAPI
import uvicorn

from auth.routes import router as auth_router
from comment.routes import router as comment_router
from photo.routes import router as photo_router
from user_profile.routes import router as user_router
from frontend.routes import router as frontend_router

app = FastAPI()

app.include_router(auth_router)
app.include_router(comment_router)
app.include_router(photo_router)
app.include_router(user_router)
app.include_router(frontend_router)


if __name__ == "__main__":
    uvicorn.run(app=app,
                host="localhost",
                port=8080)
