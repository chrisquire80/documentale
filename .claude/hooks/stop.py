#!/usr/bin/env python3
"""Stop hook — saves a session summary when Claude finishes responding.

Reads the last assistant message and observation count to persist a concise
summary for future session context injection.
"""
import sys
import json
import os
import re

sys.path.insert(0, os.path.dirname(__file__))
from memory_db import get_db, get_project_name


def _extract_request(last_message: str) -> str:
    """Best-effort extraction of what was requested from the last response."""
    # Take first non-empty, non-heading line as a task hint
    for line in last_message.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and len(line) > 10:
            return line[:200]
    return last_message[:200]


def _extract_completed(last_message: str, obs_count: int) -> str:
    lines = []
    if obs_count:
        lines.append(f"{obs_count} tool operations performed")
    # Look for bullet points in the last message that hint at completed work
    bullets = re.findall(r"^[\-\*]\s+(.+)$", last_message, re.MULTILINE)
    if bullets:
        lines.extend(b[:120] for b in bullets[:3])
    return "; ".join(lines) if lines else "Session completed"


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        hook_input = {}

    last_message = hook_input.get("last_assistant_message") or ""
    project = get_project_name()
    claude_session_id = os.environ.get("CLAUDE_SESSION_ID", "")

    try:
        conn = get_db()

        # Find the active session
        session = conn.execute(
            """
            SELECT id FROM sessions
            WHERE claude_session_id = ? AND project = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (claude_session_id, project),
        ).fetchone()

        if not session:
            conn.close()
            sys.exit(0)

        session_db_id = session["id"]

        obs_count = conn.execute(
            "SELECT COUNT(*) AS n FROM observations WHERE session_id = ?",
            (session_db_id,),
        ).fetchone()["n"]

        request_hint = _extract_request(last_message)
        completed = _extract_completed(last_message, obs_count)

        conn.execute(
            """
            INSERT INTO session_summaries
                (session_id, project, request, completed, next_steps, obs_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_db_id, project, request_hint, completed, "", obs_count),
        )

        conn.execute(
            """
            UPDATE sessions
            SET status = 'completed', completed_at = datetime('now')
            WHERE id = ?
            """,
            (session_db_id,),
        )

        conn.commit()
        conn.close()

    except Exception as exc:
        print(f"[memory/stop] error: {exc}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
