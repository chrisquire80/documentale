#!/usr/bin/env bash
# setup-qmd.sh — Initialise QMD index for the Documentale project
#
# QMD (https://github.com/tobi/qmd) provides on-device hybrid search
# (BM25 + vector + LLM re-ranking) over markdown and source files,
# making them searchable from Claude Code sessions via the MCP server.
#
# Collections created:
#   docs    — project root markdown (CLAUDE.md, README, etc.)
#   backend — backend Python source files
#
# Usage:
#   bash scripts/setup-qmd.sh          # first-time setup
#   bash scripts/setup-qmd.sh --force  # force re-embed everything
#
set -euo pipefail

FORCE=""
[[ "${1:-}" == "--force" ]] && FORCE="-f"

# ── Checks ─────────────────────────────────────────────────────────────────

if ! command -v qmd &>/dev/null; then
  echo "ERROR: qmd not found. Install with:"
  echo "  npm install -g @tobilu/qmd"
  echo "  # or: bun install -g @tobilu/qmd"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Documentale QMD setup"
echo "    Project: $PROJECT_DIR"
echo "    QMD:     $(qmd --version 2>/dev/null || echo 'unknown version')"
echo ""

# ── Collections ─────────────────────────────────────────────────────────────

echo "--> Registering collection: docs (*.md)"
qmd collection add "$PROJECT_DIR" --name docs --mask "**/*.md" 2>/dev/null || \
  echo "    (docs collection already registered)"

echo "--> Registering collection: backend (*.py)"
qmd collection add "$PROJECT_DIR/backend" --name backend --mask "**/*.py" 2>/dev/null || \
  echo "    (backend collection already registered)"

# ── Context descriptions ─────────────────────────────────────────────────────
# Context is attached to virtual qmd:// paths and injected into search results,
# helping the LLM understand what each part of the project contains.

echo "--> Adding context descriptions"
qmd context add qmd://docs \
  "Documentale DMS — project documentation, architecture, API reference, CLAUDE.md" \
  2>/dev/null || true

qmd context add qmd://docs/CLAUDE.md \
  "Main project instructions for Claude Code: architecture, models, endpoints, patterns" \
  2>/dev/null || true

qmd context add qmd://backend \
  "FastAPI backend source: models, services (OCR, Gemini, LangExtract, PageIndex), API endpoints" \
  2>/dev/null || true

qmd context add qmd://backend/app/services \
  "AI/ML services: gemini.py, langextract_service.py, pageindex_service.py, embeddings.py, ocr.py" \
  2>/dev/null || true

qmd context add qmd://backend/app/api \
  "FastAPI routers: auth, documents, ai (chat, extract, pageindex), shares, comments, admin" \
  2>/dev/null || true

# ── Embed ────────────────────────────────────────────────────────────────────

echo ""
echo "--> Generating vector embeddings (this may take a few minutes on first run)"
echo "    Models (~2GB total) are downloaded from HuggingFace on first use."
echo ""
qmd embed $FORCE

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo "==> QMD setup complete!"
echo ""
qmd status
echo ""
echo "Usage examples:"
echo "  qmd query 'how does LangExtract entity extraction work?'"
echo "  qmd search 'pgvector embedding' -c backend"
echo "  qmd vsearch 'document hierarchical indexing'"
echo "  qmd query 'FastAPI JWT authentication flow' -c backend"
echo ""
echo "MCP server (for Claude Code):"
echo "  qmd mcp              # stdio (launched automatically by Claude Code)"
echo "  qmd mcp --http       # HTTP daemon on :8181"
echo "  qmd mcp --http --daemon && qmd status"
