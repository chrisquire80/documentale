#!/usr/bin/env python3
"""SessionStart hook — injects recent memory context into Claude's session.

Anything printed to stdout is automatically prepended to Claude's context
by the Claude Code runtime.
"""
import sys
import json
import os

sys.path.insert(0, os.path.dirname(__file__))
from memory_db import get_db, get_project_name


def main() -> None:
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        hook_input = {}

    source = hook_input.get("source", "startup")
    project = get_project_name()

    try:
        conn = get_db()

        # Recent session summaries (last 5)
        summaries = conn.execute(
            """
            SELECT ss.request, ss.completed, ss.next_steps, ss.obs_count,
                   ss.created_at
            FROM session_summaries ss
            WHERE ss.project = ?
            ORDER BY ss.created_at DESC
            LIMIT 5
            """,
            (project,),
        ).fetchall()

        # Recent observations index (last 40)
        obs = conn.execute(
            """
            SELECT id, tool_name, title, created_at
            FROM observations
            WHERE project = ?
            ORDER BY created_at DESC
            LIMIT 40
            """,
            (project,),
        ).fetchall()

        conn.close()

        if not summaries and not obs:
            sys.exit(0)

        lines = [
            f"# Claude Memory — {project}",
            f"*Persistent context from previous sessions (trigger: {source})*",
            "",
        ]

        if summaries:
            lines.append("## Recent Sessions")
            for s in summaries:
                ts = s["created_at"][:16] if s["created_at"] else "unknown"
                obs_n = s["obs_count"] or 0
                lines.append(f"\n### {ts} ({obs_n} observations)")
                if s["request"]:
                    lines.append(f"**Task**: {s['request']}")
                if s["completed"]:
                    lines.append(f"**Done**: {s['completed']}")
                if s["next_steps"]:
                    lines.append(f"**Next**: {s['next_steps']}")
            lines.append("")

        if obs:
            lines.append("## Observations Index")
            lines.append("| ID | Time | Tool | Title |")
            lines.append("|----|------|------|-------|")
            for o in obs:
                ts = o["created_at"][:16] if o["created_at"] else ""
                title = (o["title"] or o["tool_name"] or "—")[:70]
                tool = o["tool_name"] or "—"
                lines.append(f"| {o['id']} | {ts} | {tool} | {title} |")
            lines.append("")

        print("\n".join(lines))
        sys.exit(0)

    except Exception as exc:
        print(f"[memory/session_start] error: {exc}", file=sys.stderr)
        sys.exit(1)  # non-blocking: logged but doesn't block Claude


if __name__ == "__main__":
    main()
