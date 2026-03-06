import asyncio
import sys
import os

sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.models.user import User, UserRole
from app.api.auth import create_access_token
from sqlalchemy import select

async def get_token():
    async with SessionLocal() as db:
        stmt = select(User).where(User.role == UserRole.ADMIN).limit(1)
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("No admin user found.")
            return
            
        token = create_access_token(data={"sub": admin.email})
        print(token)

if __name__ == "__main__":
    asyncio.run(get_token())
