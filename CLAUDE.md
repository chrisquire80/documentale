# Documentale — Business Document Management System

## Project Overview

**Documentale** is a full-stack Document Management System (DMS) with Italian language support. It provides AI-assisted document ingestion, OCR, tagging, semantic search, version control, commenting, and document sharing.

## Architecture

### Backend — `backend/`
- **Framework**: FastAPI (async) with SQLAlchemy 2.0 (asyncio)
- **Database**: PostgreSQL 15 + `pgvector` extension (HNSW indexes for vector search)
- **Cache**: Redis 7 (with `redis[hiredis]`)
- **AI**: Google Gemini API (`google-generativeai`) for OCR, tagging, and text embeddings (768 dims)
- **Auth**: JWT (python-jose) with access tokens (4h) + refresh tokens (30d)
- **Storage**: Local filesystem under `backend/storage/documents/`
- **Port**: 8000

### Frontend — `frontend/`
- **Framework**: React 18 + TypeScript + Vite
- **State**: Zustand
- **UI**: Custom components (no UI library)
- **Testing**: Vitest (unit) + Playwright (e2e)
- **Port**: 5173

### Infrastructure
- **Docker Compose**: `docker-compose.yml` (db, redis, backend, frontend)
- **Document volumes**: `docker-volumes/documents/`, `docker-volumes/auto_ingest/`
- **SonarQube**: `docker-compose.sonarqube.yml` (optional)

## Key Backend Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app, startup (DB init, FTS triggers, Redis, watcher) |
| `backend/app/core/config.py` | Pydantic settings (env vars) |
| `backend/app/core/security.py` | JWT creation/verification, password hashing |
| `backend/app/core/cache.py` | Redis connection management |
| `backend/app/core/rate_limit.py` | SlowAPI rate limiting |
| `backend/app/core/storage.py` | File storage utilities |
| `backend/app/db.py` | Async SQLAlchemy engine + session factory |
| `backend/app/api/auth.py` | `/auth/` — login, register, refresh, logout |
| `backend/app/api/documents.py` | `/documents/` — CRUD, upload, download, search |
| `backend/app/api/admin.py` | `/admin/` — user management, system stats |
| `backend/app/api/shares.py` | `/shares/` — document sharing between users |
| `backend/app/api/comments.py` | `/comments/` — per-document comments |
| `backend/app/api/ws.py` | WebSocket endpoint for real-time updates |
| `backend/app/api/ai.py` | `/ai/` — AI search, tag generation, embeddings |
| `backend/app/models/document.py` | Document, DocumentVersion, DocumentMetadata, DocumentContent, DocumentShare |
| `backend/app/models/user.py` | User model |
| `backend/app/models/comment.py` | DocumentComment model |
| `backend/app/models/share.py` | DocumentPublicShare model |
| `backend/app/models/audit.py` | Audit log model |
| `backend/app/services/gemini.py` | Gemini API client (OCR, summaries) |
| `backend/app/services/gemini_tagger.py` | AI document tagging |
| `backend/app/services/embeddings.py` | Text embedding generation |
| `backend/app/services/ocr.py` | OCR pipeline (pdfplumber + pytesseract) |
| `backend/app/services/watcher.py` | Auto-ingest watchdog for `auto_ingest/` dir |
| `backend/app/services/trash_cleanup.py` | Background 30-day trash cleanup scheduler |

## Database Schema

### Core Tables
- **`users`** — User accounts with hashed passwords and roles
- **`documents`** — Document metadata (title, file_type, version, owner, is_restricted, is_deleted)
- **`doc_versions`** — Version history with file_path and checksum
- **`doc_metadata`** — JSONB metadata (tags, dept, author, etc.) with GIN index
- **`doc_content`** — Fulltext content, Italian FTS tsvector (GIN), 768-dim embedding (HNSW cosine)
- **`document_shares`** — Restricted document sharing between users
- **`document_comments`** — Per-document comments
- **`audit_logs`** — Action audit trail

### Key Features
- **FTS**: PostgreSQL `tsvector` with Italian dictionary, updated by trigger on `doc_content`
- **Vector Search**: `pgvector` HNSW index with cosine similarity (768-dim Gemini embeddings)
- **Hybrid Search**: Combines FTS + vector search in `/ai/search`
- **Versioning**: Multiple versions per document, `current_version` pointer

## Frontend Structure

| Path | Purpose |
|------|---------|
| `frontend/src/App.tsx` | Root component, routing |
| `frontend/src/pages/` | Page-level components |
| `frontend/src/components/` | Reusable UI components |
| `frontend/src/services/` | Axios-based API service layer |
| `frontend/src/store/` | Zustand stores |
| `frontend/src/test/` | Test utilities and mocks |
| `frontend/e2e/` | Playwright end-to-end tests |

### Key Components
- `DocumentCard.tsx` — Document card with actions
- `UploadModal.tsx` — File upload with metadata
- `PreviewModal.tsx` / `DocumentPreviewModal.tsx` — Document preview
- `CommentsPanel.tsx` — Comment thread UI
- `ShareModal.tsx` — User sharing dialog
- `SidebarFilters.tsx` — Search/filter sidebar
- `BulkActionBar.tsx` / `BulkUploadModal.tsx` — Bulk operations
- `EditMetadataModal.tsx` — Inline metadata editor
- `TrashModal.tsx` — Trash/restore UI

## Development Commands

### Docker (recommended)
```bash
docker-compose up -d        # Start all services
docker-compose logs -f      # Stream logs
docker-compose down         # Stop services
docker-compose down -v      # Stop + remove volumes
```

### Backend (local)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (local)
```bash
cd frontend
npm install
npm run dev         # Vite dev server on :5173
npm run build       # Production build
npm run preview     # Preview production build
```

### Tests
```bash
# Backend
cd backend && pytest
cd backend && pytest --cov=app tests/

# Frontend unit
cd frontend && npm test
cd frontend && npm run coverage

# E2E
cd frontend && npx playwright test
cd frontend && npx playwright test --ui
```

## Environment Variables (`.env`)

```env
# Database
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=documentale

# Security
SECRET_KEY=your-secret-key-min-32-chars

# AI (optional)
GEMINI_API_KEY=your-gemini-api-key
GEMINI_ENABLED=true

# Redis
REDIS_URL=redis://redis:6379/0
```

## API Endpoints Overview

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create user account |
| POST | `/auth/login` | Login, get JWT tokens |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/documents/` | List documents (paginated, filterable) |
| POST | `/documents/upload` | Upload document (multipart) |
| GET | `/documents/{id}` | Get document metadata |
| GET | `/documents/{id}/download` | Download document file |
| PUT | `/documents/{id}` | Update metadata |
| DELETE | `/documents/{id}` | Soft-delete (trash) |
| POST | `/documents/{id}/restore` | Restore from trash |
| GET | `/documents/search` | Full-text search |
| POST | `/ai/search` | Semantic/hybrid search |
| POST | `/ai/tag` | Generate AI tags for document |
| GET | `/comments/{doc_id}` | List comments |
| POST | `/comments/{doc_id}` | Add comment |
| GET | `/shares/{doc_id}` | List shares |
| POST | `/shares/{doc_id}` | Share with user |
| GET | `/admin/users` | Admin: list users |
| WS | `/ws/{client_id}` | WebSocket for real-time updates |

## Memory System

This project uses a persistent memory system for Claude Code sessions, inspired by [claude-mem](https://github.com/thedotmack/claude-mem).

- **Hooks**: `.claude/hooks/` — Python scripts for lifecycle events
- **Storage**: `~/.documentale-mem/memory.db` (SQLite, gitignored)
- **Context**: Recent sessions and observations auto-injected at session start
- **Configuration**: `.claude/settings.json`

The memory system captures tool usage, session summaries, and key observations to maintain continuity across Claude Code sessions working on this codebase.

## Common Patterns

### Adding a New API Endpoint
1. Add route to `backend/app/api/<module>.py`
2. Add Pydantic schema to `backend/app/schemas/<module>_schemas.py`
3. Include router in `backend/app/main.py` if new module
4. Add frontend service call in `frontend/src/services/`

### Adding a New Model
1. Create SQLAlchemy model in `backend/app/models/<name>.py`
2. Import in `backend/app/main.py` (for `Base.metadata.create_all`)
3. Create Pydantic schemas
4. Add tests in `backend/tests/`

### Running with Gemini Disabled
Set `GEMINI_ENABLED=false` in `.env`. AI endpoints return errors but the rest of the app works normally.
