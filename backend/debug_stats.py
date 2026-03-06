import asyncio
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.api.documents import get_documents_stats
from app.models.user import User, UserRole
from fastapi import Request

async def debug():
    async with SessionLocal() as db:
        # Mock user - test both ADMIN and regular user
        print("Testing as ADMIN...")
        admin_user = User(id="00000000-0000-0000-0000-000000000000", email="admin@example.it", role=UserRole.ADMIN)
        
        try:
            response = await get_documents_stats(
                current_user=admin_user,
                db=db
            )
            print("Success (Admin)!")
            # print(response)
        except Exception as e:
            print(f"FAILED (Admin): {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

        print("\nTesting as USER...")
        regular_user = User(id="00000000-0000-0000-0000-000000000001", email="user@example.it", role=UserRole.USER)
        try:
            response = await get_documents_stats(
                current_user=regular_user,
                db=db
            )
            print("Success (User)!")
        except Exception as e:
            print(f"FAILED (User): {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug())
