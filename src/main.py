from pathlib import Path

from fastapi import FastAPI
import uvicorn
import gunicorn
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from auth.routes import router as auth_router
from email_service.routes import router as email_router
from comment.routes import router as comment_router
from photo.routes import router as photo_router
from userprofile.routes import router as user_router
from frontend.routes import router as frontend_router
from tags.routes import router as tags_router

import middlewares.crutches as crutches

app = FastAPI()

static_path = Path(__file__).parent / 'frontend' / 'static'
app.mount("/static", StaticFiles(directory=static_path), name='static')

app.include_router(auth_router)
app.include_router(email_router)
app.include_router(comment_router)
app.include_router(photo_router)
app.include_router(user_router)
app.include_router(frontend_router)
app.include_router(tags_router)


origins = [
    "https://goit-pg5-goit-pg5-3039617b.koyeb.app/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware('http')
async def call_header_cookie_crutch(request, call_next):
    return await crutches.cookie_to_header_jwt(request, call_next)


@app.middleware('http')
async def call_response_modificator(request, call_next):
    return await crutches.modify_json_response(request, call_next)


if __name__ == "__main__":
    uvicorn.run(app=app,
                host="localhost",
                port=8000)
