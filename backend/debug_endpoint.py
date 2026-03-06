import asyncio
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.api.documents import search_documents
from app.models.user import User, UserRole
from fastapi import Request

async def debug():
    async with SessionLocal() as db:
        # Mock user
        user = User(id="00000000-0000-0000-0000-000000000000", email="admin@example.it", role=UserRole.ADMIN)
        
        # Mock request
        request = MagicMock(spec=Request)
        
        try:
            print("Calling search_documents...")
            response = await search_documents(
                request=request,
                query=None,
                tag=None,
                file_type=None,
                date_from=None,
                date_to=None,
                author=None,
                department=None,
                mode=None,
                limit=1,
                offset=0,
                current_user=user,
                db=db,
                redis=None
            )
            print("Success!")
            print(response.model_dump_json(indent=2))
        except Exception as e:
            print(f"Caught exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())
