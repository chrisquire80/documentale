#!/usr/bin/env python3
"""PostToolUse hook — captures tool observations for memory persistence.

Runs after each successful tool call. Must be fast (15s timeout).
Fire-and-forget: writes to SQLite then exits 0.
"""
import sys
import json
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_db import get_db, get_project_name, get_or_create_session

# Tools that produce no useful memory signal
_SKIP_TOOLS = frozenset(
    {
        "ListMcpResourcesTool",
        "SlashCommand",
        "Skill",
        "TodoWrite",
        "AskUserQuestion",
        "ExitPlanMode",
        "Agent",
    }
)


def _make_title(tool_name: str, tool_input: dict) -> str:
    """Derive a short, readable title from the tool invocation."""
    if tool_name in ("Read", "Write", "Edit", "NotebookEdit"):
        path = tool_input.get("file_path") or tool_input.get("notebook_path", "")
        if path:
            return f"{tool_name}: {os.path.basename(path)}"
    if tool_name == "Bash":
        cmd = (tool_input.get("command") or tool_input.get("description") or "")[:80]
        return f"Bash: {cmd}"
    if tool_name in ("Grep", "Glob"):
        pat = (tool_input.get("pattern") or "")[:50]
        return f"{tool_name}: {pat}"
    if tool_name == "WebFetch":
        url = (tool_input.get("url") or "")[:60]
        return f"WebFetch: {url}"
    if tool_name == "WebSearch":
        q = (tool_input.get("query") or "")[:60]
        return f"WebSearch: {q}"
    return tool_name


def main() -> None:
    try:
        raw = sys.stdin.read()
        hook_input = json.loads(raw)
    except Exception:
        sys.exit(0)

    tool_name = hook_input.get("tool_name", "")
    if tool_name in _SKIP_TOOLS:
        sys.exit(0)

    tool_input = hook_input.get("tool_input") or {}
    tool_response = hook_input.get("tool_response")

    project = get_project_name()
    claude_session_id = os.environ.get("CLAUDE_SESSION_ID", "")

    try:
        conn = get_db()
        session_id = get_or_create_session(conn, claude_session_id, project)

        # Truncate output to keep DB lean
        if isinstance(tool_response, dict):
            output_str = json.dumps(tool_response)[:800]
        elif isinstance(tool_response, str):
            output_str = tool_response[:800]
        else:
            output_str = ""

        title = _make_title(tool_name, tool_input)

        conn.execute(
            """
            INSERT INTO observations
                (session_id, project, tool_name, title, tool_input, tool_output)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                project,
                tool_name,
                title,
                json.dumps(tool_input)[:1200],
                output_str,
            ),
        )
        conn.commit()
        conn.close()

    except Exception as exc:
        print(f"[memory/post_tool_use] error: {exc}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
