# backend/tests/test_guests.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app_with_guests():
    from app.main import create_app
    return create_app()


@pytest.fixture
def fake_user():
    return {"user_id": "user-1", "hotel_id": "hotel-1", "role": "clerk"}


@pytest.mark.asyncio
async def test_list_guests_returns_paginated_results(app_with_guests, fake_user):
    from app.deps import get_current_user, get_supabase

    mock_guests = [
        {"id": "g-1", "hotel_id": "hotel-1", "first_name": "Jane", "last_name": "Doe",
         "doc_type": "passport", "doc_number_last4": "6789", "created_at": "2026-05-14T00:00:00Z"},
    ]

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.is_.return_value.range.return_value.execute.return_value = MagicMock(data=mock_guests, count=1)

    with patch("app.routers.guests.write_audit_log", new_callable=AsyncMock):
        app_with_guests.dependency_overrides[get_current_user] = lambda: fake_user
        app_with_guests.dependency_overrides[get_supabase] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app_with_guests), base_url="http://test") as c:
            response = await c.get("/api/v1/guests")
        app_with_guests.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_delete_guest_soft_deletes(app_with_guests, fake_user):
    from app.deps import get_current_user, get_supabase

    mock_db = MagicMock()
    mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "g-1"}])

    with patch("app.routers.guests.write_audit_log", new_callable=AsyncMock):
        app_with_guests.dependency_overrides[get_current_user] = lambda: fake_user
        app_with_guests.dependency_overrides[get_supabase] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app_with_guests), base_url="http://test") as c:
            response = await c.delete("/api/v1/guests/g-1")
        app_with_guests.dependency_overrides.clear()

    assert response.status_code == 200
    mock_db.table.return_value.update.assert_called()
    call_payload = mock_db.table.return_value.update.call_args[0][0]
    assert "deleted_at" in call_payload
