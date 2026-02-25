import asyncio
import sys
import os

# Add parent dir to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db import SessionLocal
# Import all models to ensure mapper initialization
from app.models.user import User, UserRole
from app.models.document import Document, DocumentVersion, DocumentMetadata, DocumentContent
from app.models.audit import AuditLog
from app.core.security import get_password_hash

async def create_user(email, password, role=UserRole.ADMIN):
    from app.db import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"Updating existing user {email}...")
            user.hashed_password = get_password_hash(password)
            user.role = role # Also update role if user exists
        else:
            print(f"Creating new user {email}...")
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                role=role,
                department="Executive",
                is_active=True
            )
            session.add(user)
        
        await session.commit()
        print(f"User {email} processed successfully.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed the first user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    
    asyncio.run(create_user(args.email, args.password))
