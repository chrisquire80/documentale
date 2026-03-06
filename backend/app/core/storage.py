import os
import uuid
import inspect
from abc import ABC, abstractmethod
from typing import BinaryIO, Any
import aiofiles
from .config import settings

class StorageLayer(ABC):
    @abstractmethod
    async def save_file(self, file: Any, filename: str) -> str:
        """Saves file and returns the relative path."""
        pass

    @abstractmethod
    async def get_file_path(self, relative_path: str) -> str:
        """Returns the absolute path to the file."""
        pass

    @abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        """Deletes the file."""
        pass

class LocalStorage(StorageLayer):
    def __init__(self, base_path: str = settings.STORAGE_PATH):
        self.base_path = base_path
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)

    async def save_file(self, file: Any, filename: str) -> str:
        # Prevent path traversal attacks
        safe_filename = os.path.basename(filename)

        # Use UUID prefix to ensure uniqueness atomically without race conditions
        name, ext = os.path.splitext(safe_filename)
        unique_filename = f"{uuid.uuid4().hex}_{name}{ext}"
        file_path = os.path.join(self.base_path, unique_filename)

        # Use aiofiles for async file I/O to avoid blocking event loop
        async with aiofiles.open(file_path, "wb") as f:
            # Read in chunks to avoid loading entire file in memory
            chunk_size = 1024 * 1024  # 1MB chunks
            while True:
                chunk = file.read(chunk_size)
                if inspect.iscoroutine(chunk):
                    chunk = await chunk
                if not chunk:
                    break
                await f.write(chunk)

        return os.path.relpath(file_path, self.base_path)

    async def get_file_path(self, relative_path: str) -> str:
        return os.path.join(self.base_path, relative_path)

    async def delete_file(self, relative_path: str) -> bool:
        path = await self.get_file_path(relative_path)
        try:
            if os.path.exists(path):
                os.remove(path)  # os.remove is fast enough for deletions
                return True
        except OSError:
            return False
        return False

# Dependency injection helper
def get_storage() -> StorageLayer:
    return LocalStorage()
