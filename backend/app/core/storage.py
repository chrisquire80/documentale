import os
import shutil
from abc import ABC, abstractmethod
from typing import BinaryIO
from .config import settings

class StorageLayer(ABC):
    @abstractmethod
    async def save_file(self, file: BinaryIO, filename: str) -> str:
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

    async def save_file(self, file: BinaryIO, filename: str) -> str:
        # Create subfolder based on date or category if needed
        # For simplicity, just use base path
        file_path = os.path.join(self.base_path, filename)
        
        # Ensure unique filename if exists
        counter = 1
        name, ext = os.path.splitext(filename)
        while os.path.exists(file_path):
            file_path = os.path.join(self.base_path, f"{name}_{counter}{ext}")
            counter += 1

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file, buffer)
            
        return os.path.relpath(file_path, self.base_path)

    async def get_file_path(self, relative_path: str) -> str:
        return os.path.join(self.base_path, relative_path)

    async def delete_file(self, relative_path: str) -> bool:
        path = await self.get_file_path(relative_path)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

# Dependency injection helper
def get_storage() -> StorageLayer:
    return LocalStorage()
