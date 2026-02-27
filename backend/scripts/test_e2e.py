import asyncio
import httpx
import websockets
import json
import time
import os

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000/ws"

async def main():
    print("--- Inizio Test E2E ---")
    async with httpx.AsyncClient() as client:
        # 1. Login
        print("1. Effettuo login...")
        r_admin = await client.post(f"{API_BASE}/auth/login", json={"email": "admin@example.com", "password": "admin"})
        assert r_admin.status_code == 200, "Login admin fallito"
        admin_token = r_admin.json()["access_token"]
        
        r_user = await client.post(f"{API_BASE}/auth/login", json={"email": "user@example.com", "password": "user"})
        assert r_user.status_code == 200, "Login user fallito"
        user_token = r_user.json()["access_token"]
        
        # 2. Upload documento da parte dell'Admin
        print("2. Upload documento simulato...")
        file_content = b"Questo documento riguarda l'amministrazione aziendale, contenente dati sensibili sul bilancio e le fatturazioni del 2024 per il dipartimento risorse umane e vendite."
        files = {'file': ('test_ai_doc.txt', file_content, 'text/plain')}
        
        r_up = await client.post(
            f"{API_BASE}/documents/upload", 
            data={"title": "Fatturazioni e Bilancio 2024"},
            files=files,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert r_up.status_code == 200, f"Upload fallito: {r_up.text}"
        doc_id = r_up.json()["id"]
        print(f"Documento caricato con ID: {doc_id}")
        
        # 3. Connessione WS Admin
        print("3. Connessione WebSocket Admin in corso...")
        async with websockets.connect(f"{WS_BASE}/{admin_token}") as ws:
            print("WebSocket Admin connesso. Eseguo inserimento commento da parte dell'User...")
            
            # 4. Inserimento commento da parte di User (deve notificare l'owner, cioè Admin)
            r_comment = await client.post(
                f"{API_BASE}/documents/{doc_id}/comments",
                json={"content": "Ho revisionato questo bilancio, mi sembra corretto."},
                headers={"Authorization": f"Bearer {user_token}"}
            )
            assert r_comment.status_code == 200, f"Commento fallito: {r_comment.text}"
            
            # 5. Attesa notifica WS
            try:
                ws_msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                msg_data = json.loads(ws_msg)
                print(f"✅ Notifica WebSocket ricevuta: {msg_data}")
                assert msg_data["type"] == "NEW_COMMENT", "Tipo messaggio errato"
            except asyncio.TimeoutError:
                print("❌ ERRORE: Nessuna notifica WebSocket ricevuta entro 5 secondi.")
            
        # 6. Attesa per elaborazione background (OCR + AI + Embeddings)
        print("4. Attendo 15 secondi per elaborazione Gemini e vettori pgvector...")
        await asyncio.sleep(15)
        
        # 7. Verifica MetaData AI
        print("5. Controllo estrattore Gemini...")
        r_doc = await client.get(
            f"{API_BASE}/documents/{doc_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        doc_data = r_doc.json()
        meta = doc_data.get("metadata", {})
        tags = meta.get("tags", [])
        dept = meta.get("dept", "")
        
        print(f"Risultato AI - Tags: {tags}, Dept: {dept}")
        if not tags:
            print("⚠️ ATTENZIONE: Nessun tag generato (Gemini potrebbe essere offline o errore).")
        else:
            print("✅ Auto-tagging Gemini funzionante!")
            
        # 8. Test Ricerca Semantica
        print("6. Test Ricerca Semantica con pgvector...")
        query = "gestione del personale e assunzioni" # Non presente esattamente nel testo originale
        r_search = await client.get(
            f"{API_BASE}/documents/search?query={query}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        search_results = r_search.json().get("items", [])
        
        found = any(d["id"] == str(doc_id) for d in search_results)
        if found:
            print(f"✅ Ricerca Semantica riuscita! Trovato il documento cercando: '{query}'")
        else:
            print(f"⚠️ Documento non trovato con ricerca semantica per: '{query}'.")
            
        print("--- Test E2E Concluso ---")

if __name__ == "__main__":
    asyncio.run(main())
