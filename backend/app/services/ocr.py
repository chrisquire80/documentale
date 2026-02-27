"""
Servizio OCR asincrono per l'estrazione di testo da file caricati.

Supporto per:
  - PDF  → pdfplumber  (testo nativo, accurato e veloce)
  - TXT  → lettura diretta aiofiles
  - IMG  → pytesseract con lingua italiana (richiede tesseract-ocr nel sistema)

Il servizio non lancia mai eccezioni verso i chiamanti: restituisce stringa
vuota in caso di errore e logga un warning.
"""
import asyncio
import logging
from typing import Optional

import aiofiles

logger = logging.getLogger(__name__)

# Lunghezza minima perché il testo estratto da PDF venga considerato valido.
# PDF "scansionati" (solo immagini) producono testi quasi vuoti con pdfplumber.
_MIN_PDF_TEXT_LEN = 30


async def extract_text(file_path: str, content_type: str) -> str:
    """
    Estrae il testo grezzo da un file in modo asincrono.

    Args:
        file_path:    Percorso assoluto del file su disco.
        content_type: MIME type del file (es. "application/pdf").

    Returns:
        Testo estratto (può essere stringa vuota se il file non contiene
        testo leggibile o se la libreria non è installata).
    """
    try:
        if content_type == "application/pdf":
            return await _extract_pdf(file_path)

        if content_type == "text/plain":
            return await _extract_txt(file_path)

        if content_type.startswith("image/"):
            return await _extract_image(file_path)

        if content_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return await _extract_docx(file_path)

        # Tipi non supportati → stringa vuota
        return ""

    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR fallita per '%s' (%s): %s", file_path, content_type, exc)
        return ""


# ── Estrattori privati ────────────────────────────────────────────────────────

async def _extract_pdf(path: str) -> str:
    """Estrae testo da PDF con pdfplumber (run in thread-pool per evitare blocking)."""

    def _sync() -> str:
        import pdfplumber  # lazy import: non tutti i deploy lo hanno

        with pdfplumber.open(path) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]

        return " ".join(filter(None, pages_text)).strip()

    text = await asyncio.get_event_loop().run_in_executor(None, _sync)

    # Se il testo è troppo corto probabilmente è un PDF scansionato:
    # proviamo con pytesseract su immagini delle pagine.
    if len(text) < _MIN_PDF_TEXT_LEN:
        logger.info("PDF '%s': testo nativo troppo corto (%d chars), provo OCR immagini.", path, len(text))
        ocr_text = await _ocr_pdf_pages(path)
        return ocr_text or text

    return text


async def _ocr_pdf_pages(path: str) -> str:
    """OCR di un PDF scansionato tramite pdf2image + pytesseract (best-effort)."""

    def _sync() -> str:
        try:
            from pdf2image import convert_from_path  # optional dep
            import pytesseract

            pages = convert_from_path(path, dpi=200)
            texts = [pytesseract.image_to_string(p, lang="ita") for p in pages]
            return " ".join(filter(None, texts)).strip()
        except ImportError:
            # pdf2image non installato: skip silenziosamente
            return ""

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def _extract_txt(path: str) -> str:
    """Lettura diretta di file di testo semplice."""
    async with aiofiles.open(path, "r", encoding="utf-8", errors="replace") as f:
        return (await f.read()).strip()


async def _extract_docx(path: str) -> str:
    """Estrae testo da file .docx tramite python-docx."""

    def _sync() -> str:
        from docx import Document  # lazy import

        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return " ".join(paragraphs).strip()

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def _extract_image(path: str) -> str:
    """OCR su immagine con pytesseract (lingua italiana)."""

    def _sync() -> str:
        import pytesseract
        from PIL import Image

        img = Image.open(path)
        return pytesseract.image_to_string(img, lang="ita").strip()

    return await asyncio.get_event_loop().run_in_executor(None, _sync)


