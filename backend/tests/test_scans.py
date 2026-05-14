# backend/tests/test_scans.py
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from PIL import Image
from httpx import AsyncClient, ASGITransport


def make_jpeg() -> bytes:
    img = Image.new("RGB", (200, 150), color=(100, 100, 100))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def app_with_scans():
    from app.main import create_app
    return create_app()


@pytest.fixture
def fake_user():
    return {"user_id": "user-1", "hotel_id": "hotel-1", "role": "clerk"}


@pytest.mark.asyncio
async def test_post_scans_returns_scan_id(app_with_scans, fake_user):
    from app.deps import get_current_user, get_supabase
    from app.services.vertex_ai import FakeVertexClient
    from app.models.scan import ParsedID
    from app.services.image_pipeline import PipelineResult

    fake_result = ParsedID(first_name="Jane", last_name="Doe", confidence=0.9)
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    mock_db.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"image_retention_hours": 24}
    )
    mock_db.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[{"id": "guest-1"}])
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    with (
        patch("app.routers.scans.run_pipeline") as mock_pipeline,
        patch("app.routers.scans.upload_scan_image", return_value="scans/hotel-1/scan-1.jpg"),
        patch("app.routers.scans.get_vertex_client", return_value=FakeVertexClient(response=fake_result)),
        patch("app.routers.scans.write_audit_log", new_callable=AsyncMock),
    ):
        mock_pipeline.return_value = PipelineResult(
            image_bytes=make_jpeg(), face_region_blacked_out=True, scan_id="scan-1"
        )

        app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
        app_with_scans.dependency_overrides[get_supabase] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
            response = await c.post(
                "/api/v1/scans",
                files={"file": ("id.jpg", make_jpeg(), "image/jpeg")},
            )
        app_with_scans.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert "id" in body["data"]


@pytest.mark.asyncio
async def test_post_scans_rejects_oversized_file(app_with_scans, fake_user):
    from app.deps import get_current_user, get_supabase

    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
    app_with_scans.dependency_overrides[get_supabase] = lambda: mock_db
    async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
        response = await c.post(
            "/api/v1/scans",
            files={"file": ("big.jpg", b"x" * (9 * 1024 * 1024), "image/jpeg")},
        )
    app_with_scans.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_scan_by_id_returns_scan(app_with_scans, fake_user):
    from app.deps import get_current_user, get_supabase

    mock_scan = {
        "id": "scan-1", "hotel_id": "hotel-1", "status": "parsed",
        "face_region_blacked_out": True, "parsed_data": {},
        "created_at": "2026-05-14T00:00:00Z", "parsed_at": None, "typed_at": None, "error_message": None,
    }

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=mock_scan)

    with patch("app.routers.scans.write_audit_log", new_callable=AsyncMock):
        app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
        app_with_scans.dependency_overrides[get_supabase] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
            response = await c.get("/api/v1/scans/scan-1")
        app_with_scans.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "scan-1"


@pytest.mark.asyncio
async def test_get_scan_wrong_hotel_returns_404(app_with_scans, fake_user):
    from app.deps import get_current_user, get_supabase

    mock_db = MagicMock()
    mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=None)

    with patch("app.routers.scans.write_audit_log", new_callable=AsyncMock):
        app_with_scans.dependency_overrides[get_current_user] = lambda: fake_user
        app_with_scans.dependency_overrides[get_supabase] = lambda: mock_db
        async with AsyncClient(transport=ASGITransport(app=app_with_scans), base_url="http://test") as c:
            response = await c.get("/api/v1/scans/other-hotel-scan")
        app_with_scans.dependency_overrides.clear()

    assert response.status_code == 404
