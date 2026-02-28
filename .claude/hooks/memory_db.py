"""Shared SQLite utilities for the Documentale memory system."""
import sqlite3
import os
from pathlib import Path

# Store DB in user's home directory (not inside the project)
DB_DIR = Path.home() / ".documentale-mem"
DB_PATH = DB_DIR / "memory.db"


def get_project_name() -> str:
    """Get project name from CLAUDE_PROJECT_DIR or cwd."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(project_dir).name


def get_db() -> sqlite3.Connection:
    """Open and return a SQLite connection, creating schema if needed."""
    DB_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        PRAGMA journal_mode=WAL;

        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            claude_session_id TEXT,
            project         TEXT NOT NULL,
            status          TEXT DEFAULT 'active',
            created_at      TEXT DEFAULT (datetime('now')),
            completed_at    TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_sessions_project
            ON sessions(project);
        CREATE INDEX IF NOT EXISTS idx_sessions_created
            ON sessions(created_at DESC);

        CREATE TABLE IF NOT EXISTS observations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER REFERENCES sessions(id),
            project         TEXT NOT NULL,
            tool_name       TEXT,
            title           TEXT,
            tool_input      TEXT,
            tool_output     TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_obs_session
            ON observations(session_id);
        CREATE INDEX IF NOT EXISTS idx_obs_project
            ON observations(project);
        CREATE INDEX IF NOT EXISTS idx_obs_created
            ON observations(created_at DESC);

        CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
            title,
            tool_input,
            content=observations,
            content_rowid=id
        );

        CREATE TABLE IF NOT EXISTS session_summaries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER REFERENCES sessions(id),
            project         TEXT NOT NULL,
            request         TEXT,
            completed       TEXT,
            next_steps      TEXT,
            obs_count       INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_summaries_project
            ON session_summaries(project);
        CREATE INDEX IF NOT EXISTS idx_summaries_created
            ON session_summaries(created_at DESC);
    """)
    conn.commit()


def get_or_create_session(
    conn: sqlite3.Connection, claude_session_id: str, project: str
) -> int:
    """Return the session DB id, creating a new record if necessary."""
    row = conn.execute(
        "SELECT id FROM sessions WHERE claude_session_id = ? AND project = ?",
        (claude_session_id, project),
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        "INSERT INTO sessions (claude_session_id, project) VALUES (?, ?)",
        (claude_session_id, project),
    )
    conn.commit()
    return cursor.lastrowid
