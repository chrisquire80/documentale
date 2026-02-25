from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .db import engine, Base

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # In a real app, use Alembic. For this prototype, we create tables on startup.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

from .api import auth, documents
app.include_router(auth.router)
app.include_router(documents.router)

@app.get("/")
async def root():
    return {"message": "DMS API is running"}
