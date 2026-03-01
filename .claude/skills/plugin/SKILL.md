---
name: plugin
description: Use when creating, modifying, registering, or debugging a Documentale plugin. Invoke for new plugin hooks, built-in plugin development, plugin enable/disable, or integrating plugin metadata into the document pipeline.
license: MIT
metadata:
  author: Documentale
  version: "1.0.0"
  domain: backend
  triggers: plugin, hook, on_ocr_complete, on_metadata_extracted, on_document_uploaded, on_document_deleted, on_document_downloaded, DocumentPlugin, registry, plugin_manager, word_count, content_classifier
  role: specialist
  scope: implementation
  output-format: code
  related-skills: fastapi-expert, python-pro
---

# Documentale Plugin Developer

Specialist for creating and integrating plugins into the Documentale DMS plugin system.

## System Overview

The plugin system lives in `backend/app/plugins/` and provides lifecycle hooks into the document processing pipeline.

```
backend/app/plugins/
  __init__.py          ← public surface (registry, plugin_manager, base classes)
  base.py              ← DocumentPlugin ABC + context dataclasses
  registry.py          ← PluginRegistry singleton
  manager.py           ← PluginManager (fires hooks, aggregates results)
  built_in/
    word_count.py      ← adds word/char stats to metadata
    content_classifier.py  ← infers document type from keywords
```

Plugin registration happens in `backend/app/main.py`:
```python
registry.register(WordCountPlugin())
```

## Available Hooks

| Hook | When it fires | Return value |
|------|--------------|-------------|
| `on_document_uploaded(ctx: UploadContext)` | After file is saved + initial DB row created | `dict` merged into metadata, or `None` |
| `on_ocr_complete(ctx: OCRContext)` | After OCR text extraction | replacement `str`, or `None` to keep original |
| `on_metadata_extracted(ctx: MetadataContext)` | After AI metadata + LangExtract entities | `dict` merged into metadata, or `None` |
| `on_document_deleted(ctx: DeleteContext)` | After soft-delete commits | `None` (fire-and-forget) |
| `on_document_downloaded(ctx: DownloadContext)` | Before streaming file to client | `None` (fire-and-forget) |
| `on_startup()` | App startup | `None` |
| `on_shutdown()` | App shutdown | `None` |

## Context Fields

```python
UploadContext:   doc_id, filename, content_type, owner_id, corpus, metadata
OCRContext:      doc_id, filename, extracted_text, content_type
MetadataContext: doc_id, filename, metadata, corpus   ← corpus = full OCR text
DeleteContext:   doc_id, user_id, title
DownloadContext: doc_id, user_id, filename
```

## Core Workflow

1. **Identify hook** — which lifecycle event should trigger the plugin?
2. **Create file** — `backend/app/plugins/built_in/<name>.py`
3. **Subclass `DocumentPlugin`** — set `name`, `version`, `description`; override only needed hooks
4. **Register** — add `registry.register(MyPlugin())` in `main.py`
5. **Test** — write a pytest unit test in `backend/tests/test_plugins.py`

## Minimal Plugin Template

```python
from typing import Optional
from ..base import DocumentPlugin, MetadataContext   # adjust import for location

class MyPlugin(DocumentPlugin):
    name = "my_plugin"
    version = "1.0.0"
    description = "One-line description of what this plugin does."

    async def on_metadata_extracted(self, ctx: MetadataContext) -> Optional[dict]:
        if not ctx.corpus:
            return None
        return {"my_field": "computed_value"}
```

Register in `main.py`:
```python
from .plugins.built_in.my_plugin import MyPlugin
registry.register(MyPlugin())
```

## REST API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/plugins/` | admin | List all plugins + enabled status |
| `PATCH` | `/plugins/{name}` | admin | `{"enabled": false}` to disable at runtime |

## Constraints

### MUST DO
- Override **only** the hooks your plugin needs; leave others at base no-op
- Return `None` (not `{}`) when the plugin has nothing to contribute
- Handle exceptions internally — never let a plugin crash the pipeline
- Keep `name` unique across all plugins (registry rejects duplicates with a warning)
- Write `async def` for all hooks (even if synchronous — they are awaited)

### MUST NOT DO
- Import `SessionLocal` or touch the database directly inside a plugin
- Block the event loop with synchronous I/O (use `asyncio.to_thread` if needed)
- Raise exceptions from hook methods (they are silently caught by the manager)
- Use `__init__` with required parameters (plugins are instantiated with no args)

## Testing Pattern

```python
import pytest
from app.plugins.built_in.word_count import WordCountPlugin
from app.plugins.base import MetadataContext
import uuid

@pytest.mark.asyncio
async def test_word_count_adds_stats():
    plugin = WordCountPlugin()
    ctx = MetadataContext(
        doc_id=uuid.uuid4(),
        filename="test.pdf",
        metadata={},
        corpus="Hello world this is a test",
    )
    result = await plugin.on_metadata_extracted(ctx)
    assert result["word_count"] == 6
    assert result["char_count"] == 26

@pytest.mark.asyncio
async def test_word_count_empty_corpus():
    plugin = WordCountPlugin()
    ctx = MetadataContext(doc_id=uuid.uuid4(), filename="x.pdf", metadata={}, corpus="")
    assert await plugin.on_metadata_extracted(ctx) is None
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Returning `{}` instead of `None` | An empty dict still triggers a `current_json.update({})` — return `None` |
| Blocking async with `time.sleep` | Use `await asyncio.sleep()` or `asyncio.to_thread(blocking_fn)` |
| Plugin not firing | Check `plugin.enabled` (defaults `True`); confirm it's registered before startup |
| Metadata field silently dropped | LangExtract-reserved keys (`doc_type`, `parties`, etc.) take precedence — use a different key |
| Plugin crashes silently | `PluginManager` logs errors but continues; check backend logs at `ERROR` level |
