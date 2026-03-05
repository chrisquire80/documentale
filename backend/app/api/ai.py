from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import text, update as sa_update, and_, or_, cast
from pgvector.sqlalchemy import Vector
import re
import google.generativeai as genai
from uuid import UUID

from ..db import get_db
from ..models.user import User
from ..models.document import Document, DocumentContent, DocumentMetadata
from ..api.auth import get_current_user
from ..schemas.ai_schemas import (
    ChatQueryRequest, ChatResponse, ChatSource, ExtractEntitiesResponse,
)
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

    try:
        print(f"RAG: Ricevuta query '{request.query}' per doc_id={request.document_id}")
        query_embedding = await generate_query_embedding(request.query)
    except Exception as error:
        print(f"RAG ERROR: Generazione embedding fallita: {error}")
        raise HTTPException(status_code=500, detail=f"Errore generazione embedding: {str(error)}")

    if not query_embedding:
        print("RAG ERROR: Embedding nullo")
        raise HTTPException(status_code=500, detail="Impossibile generare l'embedding per la query.")

    print(f"RAG: Eseguo ricerca vettoriale...")
    # 2. Cerca nel database con pgvector usando l'ORM per il corretto cast vettoriale
    stmt = (
        select(
            DocumentContent.document_id,
            DocumentContent.fulltext_content,
            Document.title,
            Document.is_restricted,
            Document.status,
            Document.current_version_id,
            DocumentContent.embedding.cosine_distance(cast(query_embedding, Vector)).label("distance")
        )
        .join(Document, DocumentContent.document_id == Document.id)
        .where(
            Document.is_deleted == False,
            DocumentContent.embedding.isnot(None)
        )
    )

    role = getattr(current_user, "role", None)
    if role and getattr(role, "value", role) != "ADMIN":
        dept = getattr(current_user, "department", None)
        stmt = stmt.where(
            or_(
                Document.department == dept,
                Document.department == "Generale",
                Document.department.is_(None),
                Document.owner_id == current_user.id
            )
        ).where(
            or_(
                Document.is_restricted == False,
                Document.owner_id == current_user.id
            )
        )
    if request.document_ids and len(request.document_ids) >= 2:
        stmt = stmt.where(Document.id.in_(request.document_ids))
    elif request.document_id:
        stmt = stmt.where(Document.id == request.document_id)

    # Ordina per similarità (distanza coseno minore = più simile) e limita
    stmt = stmt.order_by("distance").limit(5)

    try:
        results = await db.execute(stmt)
        rows = results.fetchall()
        print(f"RAG: Trovati {len(rows or [])} documenti pertinenti.")
    except Exception as e:
        print(f"RAG ERROR: Query database fallita: {e}")
        raise HTTPException(status_code=500, detail=f"Errore query database vettoriale: {str(e)}")

    # 3. Prepara il contesto
    if not rows:
        return ChatResponse(
            answer="Non ho trovato documenti pertinenti nel tuo archivio per rispondere a questa domanda.",
            sources=[]
        )

    context_text = ""
    sources = []
    doc_versions_used = []
    has_newer_drafts = False

    for row in rows:
        # row: document_id, fulltext_content, title, is_restricted, status, current_version_id, distance
        doc_id = str(row[0])
        fulltext = row[1] or ""
        title = row[2]
        status_val = getattr(row[4], "value", row[4]) if row[4] else None
        curr_ver_id = row[5]

        if curr_ver_id:
            doc_versions_used.append({"doc_id": doc_id, "ver_id": curr_ver_id})

        if status_val == "draft":
            has_newer_drafts = True

        # Estrai il numero di pagina se presente (es. [[PAGE:1]])
        page_match = re.search(r"\[\[PAGE:(\d+)\]\]", fulltext[:1000])
        page_num = int(page_match.group(1)) if page_match else None
        
        # Prendi un estratto (rimuovendo i tag tecnici per la visualizzazione)
        clean_text = re.sub(r"\[\[PAGE:\d+\]\]", "", fulltext or "")

        # Prova a centrare l'estratto intorno a parole chiave della query (es. "SSO")
        # in modo che il contesto includa i paragrafi realmente pertinenti.
        query_lower = (request.query or "").lower()
        keywords = []
        for token in ["sso", "single sign-on"]:
            if token in query_lower:
                keywords.append(token)

        start_idx = 0
        if keywords:
            # Cerca la prima occorrenza di una keyword nel testo
            text_lower = clean_text.lower()
            positions = [text_lower.find(k) for k in keywords if text_lower.find(k) != -1]
            if positions:
                pos = min(positions)
                window = 2000  # caratteri prima e dopo la keyword
                start_idx = max(pos - window, 0)

        max_len = 4000  # estrai fino a 4000 caratteri per documento
        snippet = clean_text[start_idx:start_idx + max_len]
        if start_idx + max_len < len(clean_text):
            snippet = snippet + "..."
        
        page_info = f" (Pagina {page_num})" if page_num else ""
        context_text += f"\n--- Documento: {title}{page_info} (ID: {doc_id}) ---\n{snippet}\n"
        
        sources.append(ChatSource(
            document_id=doc_id,
            title=title,
            snippet=snippet[:150] + "...",
            page_number=page_num
        ))

    warning_message = None
    if has_newer_drafts:
        warning_msg = "Attenzione: uno o più documenti estratti sono in stato DRAFT e potrebbero contenere informazioni non ancora approvate."
        context_text = f"[NOTA PER AI E UTENTE: {warning_msg}]\n\n" + context_text
        warning_message = warning_msg

    # 4. prompt Gemini con Retrieval-Augmented Generation
    prompt = f"""
Sei un assistente aziendale intelligente e professionale. Prima di rispondere, esegui i tuoi passi di ragionamento in italiano.

CONTESTO DOCUMENTI:
{context_text}

DOMANDA UTENTE: {request.query}

ISTRUZIONI:
1. Prima di rispondere, elenca i tuoi passaggi logici in una sezione delimitata ESATTAMENTE così:
---RAGIONAMENTO---
1. [primo passo]
2. [secondo passo]
3. [eventuale passo aggiuntivo]
---FINE RAGIONAMENTO---
2. Poi scrivi la risposta definitiva in italiano, concisa e professionale.
3. Cita sempre le fonti precise con il nome del documento e la pagina se disponibile.
4. Se la risposta non è nel contesto, dichiaralo chiaramente senza inventare.
"""

    try:
        print("RAG: Configurazione Gemini...")
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")

        print("RAG: Invio prompt a Gemini...")
        import asyncio
        response = await asyncio.to_thread(model.generate_content, prompt)

        if not response or not response.text:
            print("RAG ERROR: Risposta Gemini vuota o nulla")
            answer = "Mi dispiace, Gemini non ha generato una risposta valida."
            reasoning_steps = []
        else:
            raw_text = response.text
            print(f"RAG: Risposta generata con successo ({len(raw_text)} caratteri).")

            import re as _re
            reasoning_steps = []
            reasoning_match = _re.search(
                r'---RAGIONAMENTO---\s*(.+?)\s*---FINE RAGIONAMENTO---',
                raw_text, _re.DOTALL
            )
            if reasoning_match:
                steps_text = reasoning_match.group(1).strip()
                for line in steps_text.split('\n'):
                    line = line.strip()
                    line = _re.sub(r'^\d+\.\s*', '', line)
                    if line:
                        reasoning_steps.append(line)
                answer = _re.sub(
                    r'---RAGIONAMENTO---.*?---FINE RAGIONAMENTO---\s*',
                    '', raw_text, flags=_re.DOTALL
                ).strip()
            else:
                # No structured reasoning block — use full response as answer
                answer = raw_text.strip()
    except Exception as e:
        print(f"RAG ERROR: Fallimento durante la generazione con Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Errore chiamata Gemini: {str(e)}")

    from ..models.audit import AuditLog
    try:
        for use in doc_versions_used:
            audit = AuditLog(
                user_id=current_user.id,
                action="AI_CHAT",
                target_id=UUID(use["doc_id"]),
                document_version_id=use["ver_id"],
                query=request.query,
                ai_response=answer
            )
            db.add(audit)
        await db.commit()
    except Exception as e:
        print(f"RAG WARNING: Impossibile salvare audit log: {e}")

    return ChatResponse(
        answer=answer,
        sources=sources,
        reasoning_steps=reasoning_steps,
        warning=warning_message
    )


# ── LangExtract: on-demand structured entity extraction ──────────────────────

@router.post("/extract/{doc_id}", response_model=ExtractEntitiesResponse)
async def extract_document_entities(
    doc_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Esegue (o ri-esegue) l'estrazione strutturata di entità tramite LangExtract
    sul testo OCR già memorizzato del documento indicato.

    Le entità vengono salvate in DocumentMetadata.metadata_json e restituite
    nella risposta. L'utente deve essere proprietario o ADMIN.
    """
    from ..services.langextract_service import extract_entities, entities_to_metadata_patch
    from ..models.user import UserRole

    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Integrazione Gemini/LangExtract non configurata.",
        )

    # Recupera documento e verifica accesso
    doc_stmt = select(Document).where(Document.id == doc_id, Document.is_deleted == False)
    doc = (await db.execute(doc_stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento non trovato.")
    if doc.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Accesso negato.")

    # Recupera il testo OCR
    content_stmt = select(DocumentContent).where(DocumentContent.document_id == doc_id)
    content_row = (await db.execute(content_stmt)).scalar_one_or_none()
    ocr_text = (content_row.fulltext_content or "") if content_row else ""

    if not ocr_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Nessun testo disponibile per l'estrazione (OCR non ancora completato?).",
        )

    # Esegui LangExtract
    entities = await extract_entities(ocr_text, api_key=settings.GEMINI_API_KEY)
    patch = entities_to_metadata_patch(entities)

    # Persisti in metadata_json
    meta_stmt = select(DocumentMetadata).where(DocumentMetadata.document_id == doc_id)
    meta = (await db.execute(meta_stmt)).scalar_one_or_none()
    if meta:
        current_json = dict(meta.metadata_json or {})
        for key in ("extracted_entities", "doc_type", "parties", "dates", "amounts", "references"):
            value = patch.get(key)
            if value:
                current_json[key] = value
        meta.metadata_json = current_json
        await db.commit()

    return ExtractEntitiesResponse(
        document_id=str(doc_id),
        entity_count=len(entities),
        doc_type=patch.get("doc_type"),
        parties=patch.get("parties", []),
        dates=patch.get("dates", []),
        amounts=patch.get("amounts", []),
        references=patch.get("references", []),
        extracted_entities=entities,
    )


# ── Batch Reindex (Admin) ──────────────────────────────────────────────────────

@router.post("/reindex", status_code=202)
async def reindex_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint admin: rigenera gli embedding per tutti i documenti che non ne hanno uno.
    Risponde subito con 202 Accepted; il lavoro avviene in background.
    """
    from ..models.user import UserRole
    from ..services.embeddings import generate_embedding
    from ..db import SessionLocal
    import asyncio

    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo gli amministratori possono eseguire il reindex.")

    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini non configurato.")

    # Cerca tutti i DocumentContent senza embedding
    stmt = (
        select(DocumentContent.document_id, DocumentContent.fulltext_content)
        .where(DocumentContent.embedding.is_(None))
    )
    rows = (await db.execute(stmt)).all()
    total = len(rows)
    print(f"REINDEX: trovati {total} documenti senza embedding.")

    async def _background_reindex():
        success, failed = 0, 0
        async with SessionLocal() as session:
            for doc_id, fulltext in rows:
                try:
                    emb = await generate_embedding(fulltext or "")
                    if emb:
                        await session.execute(
                            sa_update(DocumentContent)
                            .where(DocumentContent.document_id == doc_id)
                            .values(embedding=emb)
                        )
                        await session.commit()
                        success += 1
                        print(f"REINDEX: embedding generato per {doc_id}")
                    else:
                        failed += 1
                        print(f"REINDEX WARN: embedding nullo per {doc_id}")
                except Exception as e:
                    failed += 1
                    print(f"REINDEX ERROR per {doc_id}: {e}")
                    await session.rollback()
                # Piccola pausa per non saturare la quota API
                await asyncio.sleep(0.5)
        print(f"REINDEX completato: {success} successi, {failed} fallimenti su {total}.")

    import asyncio
    asyncio.create_task(_background_reindex())

    return {"message": f"Reindex avviato in background per {total} documenti.", "total": total}


# ── Smart Query Suggestions ───────────────────────────────────────────────────

@router.post("/suggestions", response_model=None)
async def get_query_suggestions(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Genera 3 domande suggerite che un utente potrebbe fare al sistema RAG.
    Se document_id / document_title sono forniti, i suggerimenti sono contestuali.
    Risposta: {"suggestions": ["...", "...", "..."]}
    """
    from ..schemas.ai_schemas import SuggestionsResponse
    import asyncio

    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        return {"suggestions": []}

    document_title = request.get("document_title")
    document_id_raw = request.get("document_id")

    # Se ho un documento specifico, cerco di basare i suggerimenti sul suo contenuto reale
    context_snippet = ""
    if document_id_raw:
        from uuid import UUID as PyUUID
        from sqlalchemy import select as sa_select

        try:
            doc_uuid = PyUUID(str(document_id_raw))
            stmt = (
                sa_select(DocumentContent.fulltext_content, Document.title)
                .join(Document, DocumentContent.document_id == Document.id)
                .where(
                    Document.id == doc_uuid,
                    Document.is_deleted == False,
                )
            )
            row = (await db.execute(stmt)).one_or_none()
            if row:
                fulltext, db_title = row
                # Usa il titolo dal DB se disponibile
                if db_title:
                    document_title = db_title
                # Usa quanto più testo possibile (fino a ~12k caratteri) per massimizzare
                # la probabilità che le domande suggerite abbiano risposta nel contesto.
                text = (fulltext or "").strip()
                if text:
                    context_snippet = text[:12000]
        except Exception:
            # In caso di problemi, ricadiamo sulla generazione generica basata solo sul titolo
            context_snippet = ""

    if context_snippet:
        # Suggerimenti garantiti come "answerable": le domande devono poter trovare risposta nel testo fornito
        prompt = (
            "Sei un assistente aziendale. Ti fornisco il contenuto (o un estratto) di un documento.\n\n"
            f"TITOLO: {document_title or 'Documento senza titolo'}\n\n"
            "TESTO DEL DOCUMENTO:\n"
            f"{context_snippet}\n\n"
            "Genera esattamente 3 domande brevi e utili che un utente potrebbe fare, "
            "ma SOLO se la risposta è effettivamente presente o chiaramente deducibile dal testo fornito. "
            "Se una domanda non può trovare risposta nel testo, NON proporla. "
            "Rispondi SOLO con le 3 domande, una per riga, senza numerazione o prefissi."
        )
    elif document_title:
        prompt = (
            f"Sei un assistente aziendale. L'utente sta visualizzando il documento '{document_title}'. "
            "Genera esattamente 3 domande brevi e utili che l'utente potrebbe fare su questo documento. "
            "Evita domande troppo specifiche che potrebbero richiedere dettagli non presenti nel documento. "
            "Rispondi SOLO con le 3 domande, una per riga, senza numerazione o prefissi."
        )
    else:
        prompt = (
            "Sei un assistente aziendale con accesso ad un archivio di documenti. "
            "Genera esattamente 3 domande brevi e utili che un utente potrebbe porre all'archivio documentale. "
            "Rispondi SOLO con le 3 domande, una per riga, senza numerazione o prefissi."
        )

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip() if response and response.text else ""
        suggestions = [s.strip() for s in text.split("\n") if s.strip()][:3]
    except Exception:
        suggestions = []

    return {"suggestions": suggestions}


# ── Multi-Document Comparison ─────────────────────────────────────────────────

@router.post("/compare", response_model=None)
async def compare_documents(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confronta 2-10 documenti selezionati generando un'analisi comparativa tramite Gemini.
    Body: {"doc_ids": ["uuid1", "uuid2", ...]}
    """
    from ..models.user import UserRole
    import asyncio

    if not settings.GEMINI_ENABLED or not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="Gemini non configurato.")

    doc_ids_raw = request.get("doc_ids", [])
    if len(doc_ids_raw) < 2:
        raise HTTPException(status_code=400, detail="Seleziona almeno 2 documenti.")
    if len(doc_ids_raw) > 10:
        raise HTTPException(status_code=400, detail="Massimo 10 documenti per confronto.")

    # Parse UUIDs
    from uuid import UUID as PyUUID
    try:
        doc_ids = [PyUUID(str(d)) for d in doc_ids_raw]
    except Exception:
        raise HTTPException(status_code=400, detail="IDs non validi.")

    # Fetch documents + text
    stmt = (
        select(Document.id, Document.title, DocumentContent.fulltext_content)
        .join(DocumentContent, DocumentContent.document_id == Document.id)
        .where(
            Document.id.in_(doc_ids),
            Document.deleted_at.is_(None),
        )
    )
    # RBAC
    if current_user.role != UserRole.ADMIN:
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(Document.owner_id == current_user.id, Document.is_restricted == False)
        )

    rows = (await db.execute(stmt)).all()
    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="Documenti non trovati o accesso negato.")

    # Build context
    doc_sections = []
    for doc_id, title, fulltext in rows:
        snippet = (fulltext or "")[:2000]
        doc_sections.append(f"### Documento: {title}\n{snippet}\n")

    context = "\n---\n".join(doc_sections)

    prompt = f"""Sei un analista documentale aziendale esperto. Ti vengono forniti {len(rows)} documenti. Esegui un'analisi comparativa strutturata.

DOCUMENTI:
{context}

ISTRUZIONI:
1. Per ogni documento, scrivi un breve riassunto (2-3 frasi).
2. Poi scrivi un'ANALISI COMPARATIVA evidenziando:
   - Punti in comune
   - Differenze principali
   - Eventuali contraddizioni
   - Raccomandazioni

Formatta la risposta in Markdown italiano. Inizia con "## Riassunti" poi "## Analisi Comparativa".
"""

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = await asyncio.to_thread(model.generate_content, prompt)
        comparison_text = response.text.strip() if response and response.text else "Impossibile generare l'analisi."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore Gemini: {str(e)}")

    summaries = [
        {"document_id": str(doc_id), "title": title, "summary": (fulltext or "")[:200]}
        for doc_id, title, fulltext in rows
    ]

    return {"comparison": comparison_text, "summaries": summaries}
