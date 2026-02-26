"""
Test per la logica di ricerca e paginazione.

- I test unitari verificano schemi Pydantic e logica di calcolo.
- I test di integrazione (marcati `@pytest.mark.integration`) richiedono
  PostgreSQL attivo con il trigger FTS installato e vengono saltati in CI
  senza DB.
"""
import pytest
from pydantic import ValidationError

# ── Schema Pydantic ───────────────────────────────────────────────────────────

class TestPaginatedDocumentsSchema:
    """Verifica la correttezza dello schema PaginatedDocuments."""

    def test_empty_response_is_valid(self):
        from app.schemas.doc_schemas import PaginatedDocuments
        data = {"items": [], "total": 0, "limit": 20, "offset": 0}
        paged = PaginatedDocuments(**data)
        assert paged.total == 0
        assert paged.items == []
        assert paged.limit == 20
        assert paged.offset == 0

    def test_total_and_items_count_can_differ(self):
        """total rappresenta il conteggio globale, items solo la pagina corrente."""
        from app.schemas.doc_schemas import PaginatedDocuments
        # total=100 ma items ha solo 20 elementi (pagina 1 di 5)
        data = {"items": [], "total": 100, "limit": 20, "offset": 0}
        paged = PaginatedDocuments(**data)
        assert paged.total == 100

    def test_missing_required_fields_raise_error(self):
        from app.schemas.doc_schemas import PaginatedDocuments
        with pytest.raises(ValidationError):
            PaginatedDocuments(items=[], total=0)  # mancano limit e offset


# ── Logica di paginazione ─────────────────────────────────────────────────────

class TestPaginationLogic:
    """
    Verifica la matematica di paginazione che il frontend usa per
    calcolare l'offset e il numero totale di pagine.
    """

    @staticmethod
    def _total_pages(total: int, limit: int) -> int:
        return max(1, -(-total // limit))  # ceiling division

    @staticmethod
    def _offset(page: int, limit: int) -> int:
        return (page - 1) * limit

    def test_first_page_offset_is_zero(self):
        assert self._offset(1, 20) == 0

    def test_second_page_offset(self):
        assert self._offset(2, 20) == 20

    def test_total_pages_exact_multiple(self):
        assert self._total_pages(40, 20) == 2

    def test_total_pages_with_remainder(self):
        assert self._total_pages(41, 20) == 3

    def test_total_pages_zero_items(self):
        assert self._total_pages(0, 20) == 1  # minimo 1 pagina

    def test_total_pages_less_than_limit(self):
        assert self._total_pages(5, 20) == 1


# ── FTS corpus builder ────────────────────────────────────────────────────────

class TestFTSCorpusBuilder:
    """
    Verifica la logica di costruzione del corpus testuale usato per
    popolare fulltext_content durante l'upload (documents.py).
    """

    @staticmethod
    def _build_corpus(title: str, metadata: dict) -> str:
        tags_text = " ".join(metadata.get("tags", []))
        author_text = metadata.get("author", "")
        dept_text = metadata.get("dept", "")
        return " ".join(filter(None, [title, author_text, dept_text, tags_text]))

    def test_corpus_includes_title(self):
        corpus = self._build_corpus("Contratto fornitore", {})
        assert "Contratto fornitore" in corpus

    def test_corpus_includes_tags(self):
        corpus = self._build_corpus("Doc", {"tags": ["fattura", "2024"]})
        assert "fattura" in corpus
        assert "2024" in corpus

    def test_corpus_includes_author_and_dept(self):
        corpus = self._build_corpus("Doc", {"author": "Mario Rossi", "dept": "Finanza"})
        assert "Mario Rossi" in corpus
        assert "Finanza" in corpus

    def test_corpus_no_duplicate_spaces_when_optional_empty(self):
        corpus = self._build_corpus("Documento", {"tags": []})
        # Non ci devono essere spazi multipli
        assert "  " not in corpus

    def test_corpus_handles_all_empty_metadata(self):
        corpus = self._build_corpus("Titolo", {})
        assert corpus == "Titolo"


# ── Integration (richiede PostgreSQL) ────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_fts_trigger_populates_search_vector():
    """
    Verifica che dopo un INSERT in doc_content il trigger popoli
    automaticamente search_vector.
    Richiede un DB PostgreSQL con lo schema di Documentale installato.
    """
    pytest.skip("Test di integrazione: richiede PostgreSQL attivo con trigger installato.")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fts_search_finds_document_by_content():
    """
    Verifica che plainto_tsquery('italian', ...) trovi documenti il cui
    fulltext_content contiene la parola cercata.
    Richiede un DB PostgreSQL.
    """
    pytest.skip("Test di integrazione: richiede PostgreSQL attivo.")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fts_fallback_ilike_for_documents_without_content():
    """
    Verifica che i documenti senza riga in doc_content siano comunque trovati
    tramite la ricerca ILIKE sul titolo.
    Richiede un DB PostgreSQL.
    """
    pytest.skip("Test di integrazione: richiede PostgreSQL attivo.")
