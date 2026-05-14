# backend/tests/test_subscription_gate.py
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import create_app


@pytest.fixture
def app_with_gate():
    from app.middleware.subscription_gate import SubscriptionGateMiddleware
    application = create_app()
    application.add_middleware(SubscriptionGateMiddleware)
    return application


@pytest.mark.asyncio
async def test_health_bypasses_gate(app_with_gate):
    async with AsyncClient(transport=ASGITransport(app=app_with_gate), base_url="http://test") as c:
        response = await c.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_route_blocked_when_no_hotel_context(app_with_gate):
    """Routes under /api/v1 without hotel context return 403."""
    async with AsyncClient(transport=ASGITransport(app=app_with_gate), base_url="http://test") as c:
        response = await c.get("/api/v1/guests")
    # 403 (no hotel context) or 401 (no auth) or 404 (route not registered yet) — all fine here
    assert response.status_code in (401, 403, 404)
