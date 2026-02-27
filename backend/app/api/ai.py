from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text
import google.generativeai as genai
from uuid import UUID

from ..db import get_db
from ..models.user import User
from ..models.document import Document, DocumentContent
from ..api.auth import get_current_user
from ..schemas.ai_schemas import ChatQueryRequest, ChatResponse, ChatSource
from ..services.embeddings import generate_query_embedding
from ..core.config import settings

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatQueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini integration is disabled or not configured.")

    # 1. Genera l'embedding della domanda utente
    try:
        query_embedding = await generate_query_embedding(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore generazione embedding: {str(e)}")

    if not query_embedding:
        raise HTTPException(status_code=500, detail="Impossibile generare l'embedding per la query.")

    # 2. Cerca nel database con pgvector
    # Usiamo lo spazio vettoriale cosine distance (<=>)
    stmt = """
        SELECT c.id, c.document_id, c.fulltext_content, d.title, d.is_restricted,
               (c.embedding <=> :query_embedding::vector) as distance
        FROM doc_content c
        JOIN documents d ON c.document_id = d.id
        WHERE d.is_deleted = false 
          AND c.embedding IS NOT NULL
          AND (d.owner_id = :user_id OR d.is_restricted = false)
    """
    
    params = {
        "query_embedding": str(query_embedding),
        "user_id": str(current_user.id)
    }

    # Se document_id è specificato, confina la ricerca
    if request.document_id:
        stmt += " AND d.id = :doc_id"
        params["doc_id"] = str(request.document_id)

    # Ordina per similarità e limita
    stmt += " ORDER BY distance ASC LIMIT 5"

    try:
        results = await db.execute(text(stmt), params)
        rows = results.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore query database vettoriale: {str(e)}")

    # 3. Prepara il contesto
    if not rows:
        return ChatResponse(
            answer="Non ho trovato documenti pertinenti nel tuo archivio per rispondere a questa domanda.",
            sources=[]
        )

    context_text = ""
    sources = []
    
    for row in rows:
        # row: id, document_id, fulltext_content, title, is_restricted, distance
        doc_id = str(row[1])
        fulltext = row[2] or ""
        title = row[3]
        
        # Prendi un estratto (primi 500 caratteri)
        snippet = fulltext[:500] + "..." if len(fulltext) > 500 else fulltext
        
        context_text += f"\n--- Documento: {title} (ID: {doc_id}) ---\n{snippet}\n"
        
        sources.append(ChatSource(
            document_id=doc_id,
            title=title,
            snippet=snippet[:150] + "..." # Snippet più corto per la risposta JSON
        ))

    # 4. prompt Gemini con Retrieval-Augmented Generation
    prompt = f"""
Sei un assistente aziendale intelligente e professionale. Rispondi alla domanda dell'utente basandoti ESCLUSIVAMENTE sul seguente contesto estratto dai documenti aziendali.

CONTESTO:
{context_text}

DOMANDA UTENTE: {request.query}

ISTRUZIONI:
- Rispondi in italiano in modo chiaro, conciso e diretto.
- Se la risposta non è presente nel contesto, dichiara apertamente che non hai informazioni sufficienti nei documenti forniti, e NON inventare nulla.
- Cita sempre le fonti (es. "In base al documento X...").
"""

    genai.configure(api_key=settings.GEMINI_API_KEY)
    # Usiamo flash o pro, optiamo per flash per velocità
    model = genai.GenerativeModel("models/gemini-1.5-flash")
    
    try:
        # Facciamo generare la risposta a Gemini (è sincrono quindi usiamo asyncio.to_thread se servisse, ma per ora lo chiamiamo in linea considerando le policy di app IO)
        import asyncio
        response = await asyncio.to_thread(model.generate_content, prompt)
        answer = response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore chiamata Gemini: {str(e)}")

    return ChatResponse(
        answer=answer,
        sources=sources
    )
