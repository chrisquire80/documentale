import pytest
from uuid import uuid4
from app.models.document import TagStatus
from sqlalchemy import select
from app.models.document import Document, DocumentVersion, DocumentVersionTag, Tag

@pytest.mark.asyncio
async def test_tag_validation_workflow(client, auth_headers, db_session, admin_user):
    """Verifica il workflow di approvazione e rifiuto dei tag AI."""
    # 1. Setup: Creiamo un documento con un tag suggested
    # Usiamo lo store esistente o creiamo manualmente
    from uuid import uuid4
    doc_id = str(uuid4())
    
    # Per semplicità, usiamo un documento reale se possibile, o creiamone uno
    # Dato che i test di integrazione sono complessi, proviamo a usare l'API se possibile
    # Ma non abbiamo un endpoint "create mock doc with AI tags"
    # Quindi creiamo via DB
    
    doc = Document(id=doc_id, title="Test Deep Analysis", department="Legal", category="Contratto", owner_id=admin_user.id)
    db_session.add(doc)
    await db_session.flush()
    
    version = DocumentVersion(document_id=doc.id, version_num=1, file_path="dummy.pdf", ai_status="ready", ai_reasoning="Test reasoning")
    db_session.add(version)
    await db_session.flush()
    
    doc.current_version_id = version.id
    
    tag_name = f"GDPR_{uuid4().hex[:6]}"
    tag = Tag(name=tag_name)
    db_session.add(tag)
    await db_session.flush()
    
    # Associa come suggested
    dv_tag = DocumentVersionTag(
        document_version_id=version.id,
        tag_id=tag.id,
        status=TagStatus.SUGGESTED,
        page_number=5,
        is_ai_generated=True
    )
    db_session.add(dv_tag)
    await db_session.commit()
    
    # 2. Approve via API
    resp = await client.post(f"/documents/{doc_id}/tags/{tag.id}/approve", headers=auth_headers)
    assert resp.status_code == 200
    
    # 3. Verify via API
    resp = await client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Find the tag in the current_version
    tag_in_doc = next((t for t in data["current_version"]["tags"] if t["tag"]["id"] == str(tag.id)), None)
    assert tag_in_doc is not None
    assert tag_in_doc["status"] == TagStatus.VALIDATED
    
    # 4. Reject (Delete) via API
    resp = await client.delete(f"/documents/{doc_id}/tags/{tag.id}/reject", headers=auth_headers)
    assert resp.status_code == 200
    
    # 5. Verify deleted via API
    resp = await client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    tag_in_doc = next((t for t in data["current_version"]["tags"] if t["tag"]["id"] == str(tag.id)), None)
    assert tag_in_doc is None

@pytest.mark.asyncio
async def test_deep_analysis_data_exposure(client, auth_headers, db_session, admin_user):
    """Verifica che i dati di Deep Analysis siano esposti correttamente via API."""
    doc_id = str(uuid4())
    title = f"Test Deep Exposure_{uuid4().hex[:6]}"
    ai_entities = {"dates": ["2026-03-05"], "signatories": ["Mario Rossi"]}
    
    doc = Document(id=doc_id, title=title, department="Legal", category="Contratto", owner_id=admin_user.id)
    db_session.add(doc)
    await db_session.flush()
    
    version = DocumentVersion(
        document_id=doc.id, 
        version_num=1,
        file_path="dummy2.pdf",
        ai_status="ready", 
        ai_reasoning="Reasoning test",
        ai_entities=ai_entities,
        ai_summary="Short summary"
    )
    db_session.add(version)
    await db_session.flush()
    
    doc.current_version_id = version.id
    await db_session.commit()
    
    # Get via API
    # Assumiamo che ci sia un endpoint per il dettaglio documento che include l'ultima versione
    # In base a doc_schemas, DocumentResponse include ai_entities via current_version
    resp = await client.get(f"/documents/{doc_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    
    assert data["category"] == "Contratto"
    # Dati AI sono nella current_version
    ver_data = data["current_version"]
    assert ver_data["ai_reasoning"] == "Reasoning test"
    assert ver_data["ai_entities"]["dates"] == ["2026-03-05"]
    assert ver_data["ai_summary"] == "Short summary"
