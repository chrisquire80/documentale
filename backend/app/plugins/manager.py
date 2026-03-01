"""Plugin manager — fires lifecycle hooks and aggregates results."""
import logging

from .base import (
    DeleteContext,
    DownloadContext,
    MetadataContext,
    OCRContext,
    UploadContext,
)
from .registry import registry

logger = logging.getLogger(__name__)


class PluginManager:
    """Calls each enabled plugin's hooks and merges / returns results."""

    async def startup(self) -> None:
        for plugin in registry.get_enabled():
            try:
                await plugin.on_startup()
                logger.info("Plugin started: %s", plugin.name)
            except Exception as exc:
                logger.error("Plugin '%s' startup error: %s", plugin.name, exc)

    async def shutdown(self) -> None:
        for plugin in registry.get_enabled():
            try:
                await plugin.on_shutdown()
            except Exception as exc:
                logger.error("Plugin '%s' shutdown error: %s", plugin.name, exc)

    async def fire_on_document_uploaded(self, ctx: UploadContext) -> dict:
        """Returns a merged dict of all metadata patches from enabled plugins."""
        merged: dict = {}
        for plugin in registry.get_enabled():
            try:
                patch = await plugin.on_document_uploaded(ctx)
                if patch:
                    merged.update(patch)
            except Exception as exc:
                logger.error("Plugin '%s' on_document_uploaded error: %s", plugin.name, exc)
        return merged

    async def fire_on_ocr_complete(self, ctx: OCRContext) -> str:
        """Returns the (possibly modified) extracted text after all plugins run."""
        text = ctx.extracted_text
        for plugin in registry.get_enabled():
            try:
                result = await plugin.on_ocr_complete(ctx)
                if result is not None:
                    text = result
                    ctx = OCRContext(
                        doc_id=ctx.doc_id,
                        filename=ctx.filename,
                        extracted_text=text,
                        content_type=ctx.content_type,
                    )
            except Exception as exc:
                logger.error("Plugin '%s' on_ocr_complete error: %s", plugin.name, exc)
        return text

    async def fire_on_metadata_extracted(self, ctx: MetadataContext) -> dict:
        """Returns a merged dict of all metadata patches from enabled plugins."""
        merged: dict = {}
        for plugin in registry.get_enabled():
            try:
                patch = await plugin.on_metadata_extracted(ctx)
                if patch:
                    merged.update(patch)
            except Exception as exc:
                logger.error(
                    "Plugin '%s' on_metadata_extracted error: %s", plugin.name, exc
                )
        return merged

    async def fire_on_document_deleted(self, ctx: DeleteContext) -> None:
        for plugin in registry.get_enabled():
            try:
                await plugin.on_document_deleted(ctx)
            except Exception as exc:
                logger.error("Plugin '%s' on_document_deleted error: %s", plugin.name, exc)

    async def fire_on_document_downloaded(self, ctx: DownloadContext) -> None:
        for plugin in registry.get_enabled():
            try:
                await plugin.on_document_downloaded(ctx)
            except Exception as exc:
                logger.error(
                    "Plugin '%s' on_document_downloaded error: %s", plugin.name, exc
                )


# Module-level singleton
plugin_manager = PluginManager()
