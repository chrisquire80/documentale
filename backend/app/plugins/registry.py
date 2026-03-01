"""Plugin registry — singleton that holds all registered plugins."""
import logging
from typing import Optional

from .base import DocumentPlugin

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Thread-safe in-process registry for DocumentPlugin instances."""

    def __init__(self) -> None:
        self._plugins: dict[str, DocumentPlugin] = {}

    def register(self, plugin: DocumentPlugin) -> None:
        if plugin.name in self._plugins:
            logger.warning("Plugin '%s' already registered — replacing.", plugin.name)
        self._plugins[plugin.name] = plugin
        logger.info("Plugin registered: %s v%s", plugin.name, plugin.version)

    def unregister(self, name: str) -> None:
        if name in self._plugins:
            del self._plugins[name]
            logger.info("Plugin unregistered: %s", name)

    def get(self, name: str) -> Optional[DocumentPlugin]:
        return self._plugins.get(name)

    def list_all(self) -> list[DocumentPlugin]:
        return list(self._plugins.values())

    def get_enabled(self) -> list[DocumentPlugin]:
        return [p for p in self._plugins.values() if p.enabled]


# Module-level singleton used throughout the application
registry = PluginRegistry()
