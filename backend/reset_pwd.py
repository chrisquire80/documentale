"""
Script temporaneo per resettare la password admin e lanciare il reindex.
Eseguire con: python reset_pwd.py (dall'interno del container /app)
"""
import asyncio
import asyncpg
from passlib.context import CryptContext

DB_DSN = "postgresql://postgres:postgres@db:5432/documentale"
EMAIL = "admin@example.com"
NEW_PASSWORD = "Admin123!"

async def main():
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash(NEW_PASSWORD)
    print(f"Hash generato: {hashed[:20]}...")
    
    conn = await asyncpg.connect(dsn=DB_DSN)
    result = await conn.execute(
        "UPDATE users SET hashed_password = $1 WHERE email = $2",
        hashed, EMAIL
    )
    await conn.close()
    print(f"Password aggiornata. Risultato: {result}")

asyncio.run(main())
