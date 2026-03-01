"""Base classes and context objects for the Documentale plugin system."""
from abc import ABC
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID


@dataclass
class UploadContext:
    doc_id: UUID
    filename: str
    content_type: str
    owner_id: UUID
    corpus: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class OCRContext:
    doc_id: UUID
    filename: str
    extracted_text: str
    content_type: str


@dataclass
class MetadataContext:
    doc_id: UUID
    filename: str
    metadata: dict
    corpus: str = ""


@dataclass
class DeleteContext:
    doc_id: UUID
    user_id: UUID
    title: str


@dataclass
class DownloadContext:
    doc_id: UUID
    user_id: UUID
    filename: str


class DocumentPlugin(ABC):
    """Base class for all Documentale plugins.

    Subclass this and override whichever hooks you need.
    Register your plugin instance with ``registry.register(MyPlugin())``.
    """

    name: str = "base"
    version: str = "0.0.0"
    description: str = ""
    enabled: bool = True

    async def on_startup(self) -> None:
        """Called once at application startup."""

    async def on_shutdown(self) -> None:
        """Called once at application shutdown."""

    async def on_document_uploaded(self, ctx: UploadContext) -> Optional[dict]:
        """Called after a document is successfully saved.

        Return a ``dict`` to merge into the document's metadata JSON, or ``None``.
        """
        return None

    async def on_ocr_complete(self, ctx: OCRContext) -> Optional[str]:
        """Called after OCR text extraction completes.

        Return a replacement string to override the extracted text, or ``None``
        to keep the original.
        """
        return None

    async def on_metadata_extracted(self, ctx: MetadataContext) -> Optional[dict]:
        """Called after AI metadata extraction.

        Return a ``dict`` to merge into the document's metadata JSON, or ``None``.
        """
        return None

    async def on_document_deleted(self, ctx: DeleteContext) -> None:
        """Called when a document is soft-deleted (moved to trash)."""

    async def on_document_downloaded(self, ctx: DownloadContext) -> None:
        """Called when a document file is downloaded."""
