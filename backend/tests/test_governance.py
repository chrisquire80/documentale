import pytest
from uuid import uuid4
from app.models.segnalazione import StatoSegnalazione, AzioneSegnalazione
from sqlalchemy import select
from app.models.segnalazione import GovernanceSegnalazione, GovernanceSegnalazioneHistory

@pytest.mark.asyncio
async def test_create_segnalazione_and_history(client, auth_headers, db_session, admin_user):
    """Verifica che la creazione di una segnalazione generi correttamente la history."""
    doc_id = str(uuid4())
    title = f"Test Document_{uuid4().hex[:6]}"
    payload = {
        "document_title": title,
        "stato": "segnalata",
        "priorita": "alta",
        "note": "Initial note"
    }
    response = await client.post("/admin/governance/segnalazioni", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    seg_id = data["id"]
    
    # Verifica via API
    resp = await client.get(f"/admin/governance/segnalazioni/{seg_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    
    assert len(data["history"]) >= 1
    # created is usually the first event
    assert data["history"][0]["action_type"] == "created"

@pytest.mark.asyncio
async def test_update_segnalazione_status_and_history(client, auth_headers, db_session, admin_user):
    """Verifica che il cambio di stato generi un evento in history."""
    # 1. Create
    title = f"T1_{uuid4().hex[:6]}"
    payload = {"document_title": title, "stato": "segnalata", "priorita": "media"}
    resp = await client.post("/admin/governance/segnalazioni", json=payload, headers=auth_headers)
    seg_id = resp.json()["id"]
    
    # 2. Update Status
    update_payload = {"stato": "in_revisione"}
    resp = await client.patch(f"/admin/governance/segnalazioni/{seg_id}", json=update_payload, headers=auth_headers)
    assert resp.status_code == 200
    
    # 3. Verify History via API
    resp = await client.get(f"/admin/governance/segnalazioni/{seg_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    
    # Find status_changed in history
    hist = next((h for h in data["history"] if h["action_type"] == "status_changed"), None)
    assert hist is not None
    assert hist["old_value"] == "segnalata"
    assert hist["new_value"] == "in_revisione"

@pytest.mark.asyncio
async def test_update_segnalazione_assignment_and_history(client, auth_headers, db_session, admin_user):
    """Verifica che l'assegnazione generi un evento in history."""
    # 1. Create
    title = f"T2_{uuid4().hex[:6]}"
    payload = {"document_title": title, "stato": "segnalata", "priorita": "media"}
    resp = await client.post("/admin/governance/segnalazioni", json=payload, headers=auth_headers)
    seg_id = resp.json()["id"]
    
    # 2. Assign
    update_payload = {"assigned_to": str(admin_user.id)}
    resp = await client.patch(f"/admin/governance/segnalazioni/{seg_id}", json=update_payload, headers=auth_headers)
    assert resp.status_code == 200
    
    # 3. Verify History via API
    resp = await client.get(f"/admin/governance/segnalazioni/{seg_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    
    hist = next((h for h in data["history"] if h["action_type"] == "assigned"), None)
    assert hist is not None
    assert hist["new_value"] == str(admin_user.id)

@pytest.mark.asyncio
async def test_get_segnalazione_with_history(client, auth_headers, db_session, admin_user):
    """Verifica che il dettaglio includa la history ordinata."""
    # 1. Create
    title = f"T3_{uuid4().hex[:6]}"
    payload = {"document_title": title, "stato": "segnalata", "priorita": "media", "note": "Desc"}
    resp = await client.post("/admin/governance/segnalazioni", json=payload, headers=auth_headers)
    seg_id = resp.json()["id"]
    
    # 2. Update twice
    await client.patch(f"/admin/governance/segnalazioni/{seg_id}", json={"note": "Note 1"}, headers=auth_headers)
    await client.patch(f"/admin/governance/segnalazioni/{seg_id}", json={"stato": "risolta"}, headers=auth_headers)
    
    # 3. Get Detail
    resp = await client.get(f"/admin/governance/segnalazioni/{seg_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    
    assert len(data["history"]) == 3 # created, note_added, status_changed
    assert data["history"][0]["action_type"] == "created"
    assert data["history"][1]["action_type"] == "note_added"
    assert data["history"][2]["action_type"] == "status_changed"
