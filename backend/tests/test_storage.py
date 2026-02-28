"""
Test per la gestione del file storage (salvataggio, recupero, eliminazione).

Copre:
- LocalStorage implementation
- File save, retrieve, delete operations
- Path traversal attack prevention
- Async file I/O
- Error handling
"""
import pytest
import pytest_asyncio
import os
import tempfile
from io import BytesIO
from app.core.storage import LocalStorage, get_storage


# ── Fixtures ───────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def temp_storage():
    """Crea una directory temporanea per i test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = LocalStorage(base_path=tmpdir)
        yield storage
        # Cleanup è gestito automaticamente da TemporaryDirectory


@pytest_asyncio.fixture
async def sample_file():
    """Crea un file di test in memoria."""
    content = b"This is a sample test file content"
    file_obj = BytesIO(content)
    return file_obj, content


# ── Basic File Save & Retrieve ────────────────────────────────────────────────


class TestFileSaveAndRetrieve:
    """Test per salvare e recuperare file."""

    @pytest.mark.asyncio
    async def test_save_file_returns_relative_path(self, temp_storage, sample_file):
        """save_file deve restituire il percorso relativo."""
        file_obj, content = sample_file
        relative_path = await temp_storage.save_file(file_obj, "test.txt")

        assert relative_path is not None
        assert isinstance(relative_path, str)
        assert len(relative_path) > 0
        # Non dovrebbe contenere path traversal
        assert ".." not in relative_path

    @pytest.mark.asyncio
    async def test_saved_file_exists_on_disk(self, temp_storage, sample_file):
        """Un file salvato deve esistere su disco."""
        file_obj, content = sample_file
        relative_path = await temp_storage.save_file(file_obj, "test.txt")

        abs_path = await temp_storage.get_file_path(relative_path)
        assert os.path.exists(abs_path), "Il file salvato deve esistere su disco"

    @pytest.mark.asyncio
    async def test_saved_file_content_matches(self, temp_storage, sample_file):
        """Il contenuto salvato deve corrispondere al contenuto originale."""
        file_obj, original_content = sample_file
        relative_path = await temp_storage.save_file(file_obj, "test.txt")

        abs_path = await temp_storage.get_file_path(relative_path)
        with open(abs_path, "rb") as f:
            saved_content = f.read()

        assert saved_content == original_content

    @pytest.mark.asyncio
    async def test_get_file_path_returns_absolute_path(self, temp_storage):
        """get_file_path deve restituire un percorso assoluto."""
        relative = "some/relative/path.txt"
        abs_path = await temp_storage.get_file_path(relative)

        assert os.path.isabs(abs_path), "Dovrebbe restituire un percorso assoluto"
        assert relative in abs_path, "Dovrebbe contenere il percorso relativo"

    @pytest.mark.asyncio
    async def test_multiple_files_have_different_names(self, temp_storage):
        """File diversi salvati con lo stesso nome dovrebbero avere nomi diversi."""
        content1 = BytesIO(b"File 1 content")
        content2 = BytesIO(b"File 2 content")

        path1 = await temp_storage.save_file(content1, "test.txt")
        path2 = await temp_storage.save_file(content2, "test.txt")

        # I percorsi dovrebbero essere diversi (UUID garantisce unicità)
        assert path1 != path2, "File diversi devono avere percorsi diversi"


# ── File Name Handling ─────────────────────────────────────────────────────────


class TestFileNameHandling:
    """Test per la gestione dei nomi di file."""

    @pytest.mark.asyncio
    async def test_preserve_file_extension(self, temp_storage):
        """L'estensione del file deve essere preservata."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "document.pdf")

        assert relative_path.endswith(".pdf"), "L'estensione .pdf deve essere preservata"

    @pytest.mark.asyncio
    async def test_preserve_multiple_extensions(self, temp_storage):
        """Le estensioni multiple devono essere gestite."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "archive.tar.gz")

        assert relative_path.endswith(".gz"), "L'ultima estensione deve essere preservata"

    @pytest.mark.asyncio
    async def test_handle_file_without_extension(self, temp_storage):
        """I file senza estensione devono essere salvati correttamente."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "README")

        assert os.path.exists(os.path.join(temp_storage.base_path, relative_path))

    @pytest.mark.asyncio
    async def test_filename_with_special_characters(self, temp_storage):
        """I nomi con caratteri speciali devono essere gestiti."""
        content = BytesIO(b"Test content")
        # I nomi vengono normalizzati per sicurezza
        relative_path = await temp_storage.save_file(
            content, "documento@2024-01-15_draft.docx"
        )

        assert relative_path is not None
        # Dovrebbe esistere un file salvato
        abs_path = await temp_storage.get_file_path(relative_path)
        assert os.path.exists(abs_path)

    @pytest.mark.asyncio
    async def test_filename_with_spaces(self, temp_storage):
        """I nomi con spazi devono essere gestiti."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "My Document.txt")

        assert relative_path is not None
        abs_path = await temp_storage.get_file_path(relative_path)
        assert os.path.exists(abs_path)


# ── Security: Path Traversal Prevention ────────────────────────────────────────


class TestPathTraversalPrevention:
    """Test per prevenire path traversal attacks."""

    @pytest.mark.asyncio
    async def test_reject_path_traversal_with_double_dot(self, temp_storage):
        """File con ../  dovrebbero essere salvati in modo sicuro."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "../../etc/passwd")

        # Il file dovrebbe comunque essere salvato nel base_path, non in parent dirs
        abs_path = await temp_storage.get_file_path(relative_path)
        assert abs_path.startswith(temp_storage.base_path), "Deve rimanere in base_path"

    @pytest.mark.asyncio
    async def test_reject_absolute_path_in_filename(self, temp_storage):
        """I nomi assoluti dovrebbero essere normalizzati."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "/etc/passwd")

        # basename() estrae solo il nome, rimuovendo la parte di path
        assert not relative_path.startswith("/"), "Percorso relativo, non assoluto"

    @pytest.mark.asyncio
    async def test_filename_normalized_to_basename(self, temp_storage):
        """Il nome dovrebbe essere solo il basename."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(
            content, "/path/to/deep/directory/file.txt"
        )

        # Solo il basename dovrebbe essere usato
        assert "directory" not in relative_path
        assert "file.txt" in relative_path or relative_path.endswith(".txt")


# ── File Deletion ──────────────────────────────────────────────────────────────


class TestFileDeletion:
    """Test per l'eliminazione di file."""

    @pytest.mark.asyncio
    async def test_delete_existing_file(self, temp_storage):
        """Eliminare un file esistente deve restituire True."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "delete_me.txt")

        # Verifica che il file esista
        abs_path = await temp_storage.get_file_path(relative_path)
        assert os.path.exists(abs_path)

        # Elimina il file
        result = await temp_storage.delete_file(relative_path)

        # Dovrebbe restituire True e il file dovrebbe essere eliminato
        assert result is True
        assert not os.path.exists(abs_path), "Il file dovrebbe essere eliminato"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, temp_storage):
        """Eliminare un file inesistente deve restituire False."""
        result = await temp_storage.delete_file("nonexistent/file.txt")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_twice(self, temp_storage):
        """Eliminare lo stesso file due volte dovrebbe fallire la seconda volta."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "delete_twice.txt")

        # Elimina la prima volta
        result1 = await temp_storage.delete_file(relative_path)
        assert result1 is True

        # Elimina la seconda volta (dovrebbe fallire)
        result2 = await temp_storage.delete_file(relative_path)
        assert result2 is False


# ── Large File Handling ────────────────────────────────────────────────────────


class TestLargeFileHandling:
    """Test per file di grandi dimensioni."""

    @pytest.mark.asyncio
    async def test_save_large_file(self, temp_storage):
        """File grandi dovrebbero essere salvati correttamente (in chunks)."""
        # Crea un file da 5MB
        large_content = b"x" * (5 * 1024 * 1024)
        file_obj = BytesIO(large_content)

        relative_path = await temp_storage.save_file(file_obj, "large_file.bin")

        # Verifica che il file sia stato salvato
        abs_path = await temp_storage.get_file_path(relative_path)
        assert os.path.exists(abs_path)

        # Verifica la dimensione
        assert os.path.getsize(abs_path) == len(large_content)

    @pytest.mark.asyncio
    async def test_large_file_content_integrity(self, temp_storage):
        """Il contenuto di un file grande deve essere integro dopo il salvataggio."""
        # Crea un file con contenuto specifico da 2MB
        content = b"Test pattern repeated " * 100000  # ~2MB
        file_obj = BytesIO(content)

        relative_path = await temp_storage.save_file(file_obj, "integrity_test.bin")

        abs_path = await temp_storage.get_file_path(relative_path)
        with open(abs_path, "rb") as f:
            saved_content = f.read()

        assert saved_content == content, "Il contenuto deve essere identico"

    @pytest.mark.asyncio
    async def test_empty_file(self, temp_storage):
        """I file vuoti devono essere salvati correttamente."""
        empty_file = BytesIO(b"")
        relative_path = await temp_storage.save_file(empty_file, "empty.txt")

        abs_path = await temp_storage.get_file_path(relative_path)
        assert os.path.exists(abs_path)
        assert os.path.getsize(abs_path) == 0


# ── Storage Initialization ────────────────────────────────────────────────────


class TestStorageInitialization:
    """Test per l'inizializzazione dello storage."""

    @pytest.mark.asyncio
    async def test_storage_creates_directory_if_not_exists(self):
        """LocalStorage deve creare la directory se non esiste."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_storage_path = os.path.join(tmpdir, "new", "nested", "path")
            assert not os.path.exists(new_storage_path)

            storage = LocalStorage(base_path=new_storage_path)

            # La directory dovrebbe essere creata
            assert os.path.exists(new_storage_path)
            assert os.path.isdir(new_storage_path)

    @pytest.mark.asyncio
    async def test_storage_works_with_existing_directory(self, temp_storage):
        """LocalStorage deve funzionare con una directory esistente."""
        content = BytesIO(b"Test content")
        relative_path = await temp_storage.save_file(content, "test.txt")

        assert relative_path is not None
        assert len(relative_path) > 0

    @pytest.mark.asyncio
    async def test_get_storage_returns_local_storage(self):
        """get_storage() deve restituire un'istanza di LocalStorage."""
        storage = get_storage()
        assert isinstance(storage, LocalStorage)


# ── Concurrency & Race Conditions ──────────────────────────────────────────────


class TestConcurrency:
    """Test per le condizioni di concorrenza."""

    @pytest.mark.asyncio
    async def test_concurrent_file_saves(self, temp_storage):
        """File salvati concorrentemente devono avere nomi diversi."""
        import asyncio

        async def save_file(index):
            content = BytesIO(f"File {index}".encode())
            path = await temp_storage.save_file(content, f"concurrent_{index}.txt")
            return path

        # Salva 5 file concorrentemente
        paths = await asyncio.gather(*[save_file(i) for i in range(5)])

        # Tutti i percorsi devono essere diversi
        assert len(set(paths)) == 5, "Tutti i percorsi devono essere unici"

    @pytest.mark.asyncio
    async def test_uuid_prefix_uniqueness(self, temp_storage):
        """Ogni file dovrebbe avere un UUID unico come prefisso."""
        paths = []
        for i in range(10):
            content = BytesIO(f"File {i}".encode())
            path = await temp_storage.save_file(content, "same_name.txt")
            paths.append(path)

        # Tutti i percorsi devono essere diversi nonostante lo stesso nome file
        assert len(set(paths)) == 10


# ── File Type Handling ────────────────────────────────────────────────────────


class TestFileTypeHandling:
    """Test per diversi tipi di file."""

    @pytest.mark.asyncio
    async def test_save_binary_file(self, temp_storage):
        """I file binari devono essere salvati senza corruzione."""
        binary_content = bytes(range(256))  # Tutti i byte possibili
        file_obj = BytesIO(binary_content)

        relative_path = await temp_storage.save_file(file_obj, "binary.bin")

        abs_path = await temp_storage.get_file_path(relative_path)
        with open(abs_path, "rb") as f:
            saved = f.read()

        assert saved == binary_content

    @pytest.mark.asyncio
    async def test_save_text_file(self, temp_storage):
        """I file di testo devono essere salvati correttamente."""
        text_content = "Hello World\nLine 2\nLine 3"
        file_obj = BytesIO(text_content.encode("utf-8"))

        relative_path = await temp_storage.save_file(file_obj, "text.txt")

        abs_path = await temp_storage.get_file_path(relative_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            saved = f.read()

        assert saved == text_content

    @pytest.mark.asyncio
    async def test_save_unicode_filename(self, temp_storage):
        """I nomi di file con Unicode dovrebbero essere gestiti."""
        content = BytesIO(b"Test content")
        # Nomi con caratteri Unicode
        relative_path = await temp_storage.save_file(content, "документ.pdf")

        abs_path = await temp_storage.get_file_path(relative_path)
        assert os.path.exists(abs_path)
