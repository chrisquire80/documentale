"""Documentale plugin system.

Usage
-----
Register a plugin at startup::

    from app.plugins import registry
    from app.plugins.base import DocumentPlugin, MetadataContext

    class MyPlugin(DocumentPlugin):
        name = "my_plugin"
        version = "1.0.0"
        description = "Does something useful."

        async def on_metadata_extracted(self, ctx: MetadataContext):
            return {"custom_field": "value"}

    registry.register(MyPlugin())

Fire hooks (done internally by the application)::

    from app.plugins import plugin_manager
    patch = await plugin_manager.fire_on_metadata_extracted(ctx)
"""
from .base import (
    DeleteContext,
    DocumentPlugin,
    DownloadContext,
    MetadataContext,
    OCRContext,
    UploadContext,
)
from .manager import plugin_manager
from .registry import registry

__all__ = [
    "registry",
    "plugin_manager",
    "DocumentPlugin",
    "UploadContext",
    "OCRContext",
    "MetadataContext",
    "DeleteContext",
    "DownloadContext",
]
