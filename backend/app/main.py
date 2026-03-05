import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from .core.config import settings
from .core.cache import startup_redis, shutdown_redis
from .core.rate_limit import limiter
from .db import engine, Base

app = FastAPI(title=settings.PROJECT_NAME)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5001",
        "http://127.0.0.1:5001",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Disposition"],
)

from .api import auth, documents, admin, shares, comments, ws, ai
from .services import watcher
from .models.share import DocumentPublicShare
from .models.comment import DocumentComment
from .models.segnalazione import GovernanceSegnalazione  # noqa: F401 — ensures table creation

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(shares.router)
app.include_router(comments.router)
app.include_router(ws.router)
app.include_router(ai.router, prefix="/ai", tags=["AI"])


@app.on_event("startup")
async def startup():
    # In a real app, use Alembic. For this prototype, we create tables on startup.
    max_retries = 5
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                await conn.run_sync(Base.metadata.create_all)
            print("Database: tabelle create/verificate con successo, pgvector abilitato.")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(
                    f"Database: tentativo {attempt + 1}/{max_retries} fallito. "
                    f"Nuovo tentativo tra 2s... Errore: {e}"
                )
                await asyncio.sleep(2)
            else:
                print(f"Database: connessione fallita dopo {max_retries} tentativi.")
                raise e

    # Installa trigger PostgreSQL che popola automaticamente search_vector
    # da fulltext_content ad ogni INSERT/UPDATE su doc_content.
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector :=
                    to_tsvector('italian', coalesce(NEW.fulltext_content, ''));
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))
        await conn.execute(text("""
            DROP TRIGGER IF EXISTS trg_update_search_vector ON doc_content;
        """))
        await conn.execute(text("""
            CREATE TRIGGER trg_update_search_vector
                BEFORE INSERT OR UPDATE OF fulltext_content ON doc_content
                FOR EACH ROW EXECUTE FUNCTION update_search_vector();
        """))
        # GIN index per query FTS veloci (idempotente)
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_search_vector_gin
                ON doc_content USING gin(search_vector);
        """))
    print("FTS: trigger e indice GIN installati su doc_content.")

    # Avvia cache Redis
    await startup_redis()

    # Avvia servizio Watchdog in background
    watcher.start_watcher()

    # Avvia cleanup cestino (background)
    from .services.trash_cleanup import start_trash_scheduler
    asyncio.create_task(start_trash_scheduler(interval_hours=24, retention_days=30))


@app.on_event("shutdown")
async def shutdown():
    watcher.stop_watcher()
    await shutdown_redis()


@app.get("/")
async def root():
    return {"message": "DMS API is running"}
