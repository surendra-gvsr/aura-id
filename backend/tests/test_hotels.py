# backend/tests/test_hotels.py
import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def app_with_hotels():
    from app.main import create_app
    return create_app()


@pytest.mark.asyncio
async def test_get_hotel_me_returns_hotel(app_with_hotels):
    from app.deps import get_current_user, get_supabase

    fake_user = {"user_id": "u-1", "hotel_id": "hotel-1", "role": "owner"}
    mock_hotel = {
        "id": "hotel-1", "name": "Grand Hotel", "subscription_status": "active",
        "plan": "pro", "image_retention_hours": 24, "created_at": "2026-01-01T00:00:00Z",
    }

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=mock_hotel)

    app_with_hotels.dependency_overrides[get_current_user] = lambda: fake_user
    app_with_hotels.dependency_overrides[get_supabase] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app_with_hotels), base_url="http://test") as c:
        response = await c.get("/api/v1/hotels/me")
    app_with_hotels.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Grand Hotel"
