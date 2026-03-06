import asyncio
import sys
import os
import json
import urllib.request

sys.path.append(os.getcwd())

from app.db import SessionLocal
from app.models.user import User, UserRole
from app.api.auth import create_access_token
from sqlalchemy import select

async def trigger():
    async with SessionLocal() as db:
        stmt = select(User).where(User.role == UserRole.ADMIN).limit(1)
        result = await db.execute(stmt)
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("No admin user found.")
            return
            
        token = create_access_token(subject=admin.email)
        
    url = 'http://localhost:8000/documents/stats'
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    
    try:
        with urllib.request.urlopen(req) as response:
            print("Success Response:", response.read().decode())
    except Exception as e:
        if hasattr(e, 'read'):
            print("Error Response Body:", e.read().decode())
        else:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(trigger())
