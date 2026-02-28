---
name: qmd
description: Search markdown knowledge bases, notes, and documentation using QMD. Use when users ask to search notes, find documents, or look up information.
license: MIT
compatibility: Requires qmd CLI or MCP server. Install via `npm install -g @tobilu/qmd`.
metadata:
  author: tobi
  version: "2.0.0"
allowed-tools: Bash(qmd:*), mcp__qmd__*
---

# QMD - Quick Markdown Search

Local hybrid search engine for markdown content: BM25 + vector + LLM re-ranking,
all running locally via node-llama-cpp. No cloud API needed for search.

Source: https://github.com/tobi/qmd

## Status

!`qmd status 2>/dev/null || echo "Not installed: npm install -g @tobilu/qmd"`

## Documentale Collections

This project has QMD configured with two collections:

| Collection | Path | Contents |
|---|---|---|
| `docs` | `./` | CLAUDE.md, README, all project markdown |
| `backend` | `./backend/` | Python source files (*.py) |

Run `scripts/setup-qmd.sh` to initialise or re-index.

## MCP: `query`

```json
{
  "searches": [
    { "type": "lex", "query": "CAP theorem consistency" },
    { "type": "vec", "query": "tradeoff between consistency and availability" }
  ],
  "collections": ["docs"],
  "limit": 10
}
```

### Query Types

| Type | Method | Input |
|------|--------|-------|
| `lex` | BM25 | Keywords — exact terms, names, code |
| `vec` | Vector | Question — natural language |
| `hyde` | Vector | Answer — hypothetical result (50–100 words) |

### Writing Good Queries

**lex (keyword)**
- 2–5 terms, no filler words
- Exact phrase: `"connection pool"` (quoted)
- Exclude terms: `performance -sports` (minus prefix)
- Code identifiers work: `handleError async`

**vec (semantic)**
- Full natural language question
- Be specific: `"how does the rate limiter handle burst traffic"`

**hyde (hypothetical document)**
- Write 50–100 words of what the *answer* looks like

**expand (auto-expand)**
- Single-line query → local LLM generates lex/vec/hyde variations

### Combining Types

| Goal | Approach |
|---|---|
| Know exact terms | `lex` only |
| Don't know vocabulary | Single-line query (implicit `expand:`) or `vec` |
| Best recall | `lex` + `vec` |
| Complex topic | `lex` + `vec` + `hyde` |

First query gets 2× weight in fusion — put your best guess first.

## Other MCP Tools

| Tool | Use |
|------|-----|
| `get` | Retrieve doc by path or `#docid` |
| `multi_get` | Retrieve multiple by glob/list |
| `status` | Collections and health |

## CLI

```bash
qmd query "question"                       # Auto-expand + rerank (best quality)
qmd query $'lex: X\nvec: Y'               # Structured multi-type
qmd search "keywords"                     # BM25 only (fast, no LLM)
qmd vsearch "semantic question"           # Vector only
qmd get "#abc123"                          # By docid from search results
qmd multi-get "backend/app/**/*.py" -l 40  # Batch fetch by glob
qmd search "pgvector" -c backend           # Search only backend collection
```

## HTTP API (when MCP daemon is running)

```bash
curl -X POST http://localhost:8181/query \
  -H "Content-Type: application/json" \
  -d '{"searches": [{"type": "lex", "query": "langextract service"}]}'
```

## Setup

```bash
npm install -g @tobilu/qmd
bash scripts/setup-qmd.sh   # Creates collections + embeds docs
```
