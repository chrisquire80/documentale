import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from sqlalchemy import text

async def migrate():
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.connect() as conn:
        print("Aggiungendo la colonna 'assigned_to' a 'governance_segnalazioni'...")
        try:
            async with conn.begin():
                await conn.execute(text("ALTER TABLE governance_segnalazioni ADD COLUMN assigned_to UUID REFERENCES users(id) ON DELETE SET NULL;"))
        except Exception as e:
            print(f"Errore / Colonna gi esistente: {e}")

    await engine.dispose()
    print("Migrazione completata!")

if __name__ == "__main__":
    asyncio.run(migrate())
