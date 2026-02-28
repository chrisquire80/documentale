#!/usr/bin/env python3
"""UserPromptSubmit hook — creates a session record when the user submits a prompt.

Runs before Claude processes the prompt. Outputs are suppressed (suppressOutput).
Exit 0 to allow the prompt through.
"""
import sys
import json
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_db import get_db, get_project_name, get_or_create_session


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        hook_input = {}

    project = get_project_name()
    claude_session_id = os.environ.get("CLAUDE_SESSION_ID", "")

    try:
        conn = get_db()
        get_or_create_session(conn, claude_session_id, project)
        conn.close()
    except Exception as exc:
        print(f"[memory/user_prompt] error: {exc}", file=sys.stderr)

    # Always allow the prompt through; output is suppressed
    print(json.dumps({"continue": True, "suppressOutput": True}))
    sys.exit(0)


if __name__ == "__main__":
    main()
