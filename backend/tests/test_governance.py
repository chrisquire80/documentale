import pytest
from app.models.segnalazione import StatoSegnalazione, AzioneSegnalazione
from sqlalchemy import select
from app.models.segnalazione import GovernanceSegnalazione, GovernanceSegnalazioneHistory

@pytest.mark.asyncio
async def test_create_segnalazione_and_history(client, auth_headers, db_session):
    """Verifica che la creazione di una segnalazione generi correttamente la history."""
    payload = {
        "document_title": "Test Document",
        "stato": "segnalata",
        "priorita": "alta",
        "note": "Initial note"
    }
    response = await client.post("/admin/governance/segnalazioni", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    seg_id = data["id"]
    
    # Verifica DB
    stmt = select(GovernanceSegnalazioneHistory).where(GovernanceSegnalazioneHistory.segnalazione_id == seg_id)
    history = (await db_session.execute(stmt)).scalars().all()
    
    assert len(history) == 1
    assert history[0].action_type == AzioneSegnalazione.created

@pytest.mark.asyncio
async def test_update_segnalazione_status_and_history(client, auth_headers, db_session):
    """Verifica che il cambio di stato generi un evento in history."""
    # 1. Create
    payload = {"document_title": "T1", "stato": "segnalata", "priorita": "media"}
    resp = await client.post("/admin/governance/segnalazioni", json=payload, headers=auth_headers)
    seg_id = resp.json()["id"]
    
    # 2. Update Status
    update_payload = {"stato": "in_revisione"}
    resp = await client.patch(f"/admin/governance/segnalazioni/{seg_id}", json=update_payload, headers=auth_headers)
    assert resp.status_code == 200
    
    # 3. Verify History
    stmt = select(GovernanceSegnalazioneHistory).where(
        GovernanceSegnalazioneHistory.segnalazione_id == seg_id,
        GovernanceSegnalazioneHistory.action_type == AzioneSegnalazione.status_changed
    )
    history = (await db_session.execute(stmt)).scalars().all()
    assert len(history) == 1
    assert history[0].old_value == "segnalata"
    assert history[0].new_value == "in_revisione"

@pytest.mark.asyncio
async def test_update_segnalazione_assignment_and_history(client, auth_headers, db_session, admin_user):
    """Verifica che l'assegnazione generi un evento in history."""
    # 1. Create
    payload = {"document_title": "T2", "stato": "segnalata", "priorita": "media"}
    resp = await client.post("/admin/governance/segnalazioni", json=payload, headers=auth_headers)
    seg_id = resp.json()["id"]
    
    # 2. Assign
    update_payload = {"assigned_to": str(admin_user.id)}
    resp = await client.patch(f"/admin/governance/segnalazioni/{seg_id}", json=update_payload, headers=auth_headers)
    assert resp.status_code == 200
    
    # 3. Verify History
    stmt = select(GovernanceSegnalazioneHistory).where(
        GovernanceSegnalazioneHistory.segnalazione_id == seg_id,
        GovernanceSegnalazioneHistory.action_type == AzioneSegnalazione.assigned
    )
    history = (await db_session.execute(stmt)).scalars().all()
    assert len(history) == 1
    assert history[0].new_value == str(admin_user.id)

@pytest.mark.asyncio
async def test_get_segnalazione_with_history(client, auth_headers, db_session):
    """Verifica che il dettaglio includa la history ordinata."""
    # 1. Create
    payload = {"document_title": "T3", "stato": "segnalata", "priorita": "media", "note": "Desc"}
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
