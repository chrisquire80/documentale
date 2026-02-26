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

from .api import auth, documents
from .services import watcher

app.include_router(auth.router)
app.include_router(documents.router)

@app.on_event("startup")
async def startup():
    # In a real app, use Alembic. For this prototype, we create tables on startup.
    import asyncio
    max_retries = 5
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("Successfully connected to the database and created tables.")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Database connection failed (attempt {attempt + 1}/{max_retries}). Retrying in 2 seconds... Error: {e}")
                await asyncio.sleep(2)
            else:
                print(f"Failed to connect to the database after {max_retries} attempts.")
                raise e
    
    # Avvia servizio Watchdog in background
    watcher.start_watcher()

@app.on_event("shutdown")
async def shutdown():
    watcher.stop_watcher()

@app.get("/")
async def root():
    return {"message": "DMS API is running"}
