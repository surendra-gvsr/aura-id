import os

# Set dummy env vars before any app imports so Settings validation passes in tests.
# DOC_ENCRYPTION_KEY must be a valid Fernet key (url-safe base64, 32 bytes).
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-32-chars-minimum!")
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("DOC_ENCRYPTION_KEY", "mXxA7YIt-9T3eQUWxia8MR5gfOZFpjIs6kOo5Obvj_k=")

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def clerk_headers():
    """Fake JWT auth headers — override get_current_user dependency in tests."""
    return {"Authorization": "Bearer fake-clerk-jwt"}


@pytest.fixture
def workstation_headers():
    return {"Authorization": "Bearer ws_test_fakeworkstationtoken12345678901"}
