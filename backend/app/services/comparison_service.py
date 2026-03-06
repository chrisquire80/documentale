import asyncio
import logging
from uuid import UUID, uuid4
from typing import Dict, Any, List
from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from ..models.document import Document, DocumentContent, DocumentVersion, DocumentConflict, ConflictStatus
from .llm_metadata import model # Reuse the same model

logger = logging.getLogger(__name__)

async def detect_conflicts(db: AsyncSession, doc_id: UUID, new_entities: Dict[str, Any]):
    """
    Identify similar documents and use AI to detect semantic conflicts.
    """
    # 1. Get embedding for the new document
    stmt = select(DocumentContent.embedding).where(DocumentContent.document_id == doc_id)
    doc_embedding = (await db.execute(stmt)).scalar_one_or_none()
    
    if doc_embedding is None:
        return

    # 2. Find similar documents (cosine distance < 0.25)
    similar_stmt = (
        select(Document.id, Document.title, DocumentContent.embedding.cosine_distance(doc_embedding).label("distance"))
        .join(DocumentContent, Document.id == DocumentContent.document_id)
        .where(Document.id != doc_id, Document.is_deleted == False)
        .order_by("distance")
        .limit(3)
    )
    results = await db.execute(similar_stmt)
    similar_docs = results.fetchall()

    for ref_doc_id, ref_title, distance in similar_docs:
        if distance > 0.3: # Threshold
            continue
            
        logger.info(f"Conflict Analysis: Doc {doc_id} vs Ref {ref_doc_id} (Dist: {distance:.4f})")
        
        # Get reference version
        ref_stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == ref_doc_id
        ).order_by(DocumentVersion.version_num.desc()).limit(1)
        ref_ver = (await db.execute(ref_stmt)).scalar_one_or_none()
        
        if not ref_ver or not ref_ver.ai_entities:
            continue

        # 3. Use AI for semantic comparison if entities differ
        # Simple heuristic to trigger AI: compare keys
        ref_entities = ref_ver.ai_entities
        
        if _should_trigger_deep_comparison(new_entities, ref_entities):
            await _run_deep_ai_comparison(db, doc_id, ref_doc_id, ref_title, new_entities, ref_entities)

def _should_trigger_deep_comparison(e1: dict, e2: dict) -> bool:
    # Trigger if dates or amounts don't match exactly
    for key in ["dates", "amounts"]:
        if e1.get(key) != e2.get(key):
            return True
    return False

async def _run_deep_ai_comparison(db: AsyncSession, doc_id: UUID, ref_doc_id: UUID, ref_title: str, e1: dict, e2: dict):
    if not model: return

    prompt = f"""
    Sei un esperto di Compliance e Governance Aziendale.
    Confronta questi due set di metadati estratti da documenti simili e identifica conflitti semantici.
    
    DOCUMENTO NUOVO: {e1}
    DOCUMENTO RIFERIMENTO ({ref_title}): {e2}
    
    REGOLE:
    - Identifica se ci sono discrepanze reali (es. date diverse per lo stesso scopo, importi variati).
    - Ignora differenze formali trascurabili.
    - Per ogni conflitto, spiega il ragionamento.
    
    RESTITUISCI SOLO UN JSON:
    {{
        "conflicts": [
            {{
                "field": "Nome Campo (es. Data Scadenza)",
                "old_value": "Valore dal riferimento",
                "new_value": "Valore dal nuovo documento",
                "severity": "High|Medium",
                "explanation": "Spiegazione del conflitto e perchŠ Š critico"
            }}
        ]
    }}
    Se non ci sono conflitti reali, restituisci: {{"conflicts": []}}
    """

    try:
        response = await model.generate_content_async(prompt)
        content = response.text.replace("```json", "").replace("```", "").strip()
        data = asyncio.get_event_loop().run_in_executor(None, lambda: _parse_json_safely(content))
        # Wait for the thread-safe parse if needed, but since it's just json.loads:
        import json
        data = json.loads(content)
        
        for c in data.get("conflicts", []):
            db.add(DocumentConflict(
                id=uuid4(),
                document_id=doc_id,
                reference_doc_id=ref_doc_id,
                field=c.get("field", "Generale"),
                old_value=str(c.get("old_value")),
                new_value=str(c.get("new_value")),
                severity=c.get("severity", "Medium"),
                explanation=c.get("explanation"),
                status=ConflictStatus.PENDING
            ))
        await db.flush()
    except Exception as e:
        logger.error(f"Error in deep AI comparison: {e}")

def _parse_json_safely(content):
    import json
    return json.loads(content)
