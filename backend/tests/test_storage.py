# backend/tests/test_storage.py
import pytest
from unittest.mock import MagicMock
from app.services.storage import upload_scan_image, get_signed_url, delete_scan_image


@pytest.fixture
def mock_supabase():
    db = MagicMock()
    db.storage = MagicMock()
    return db


def test_upload_scan_image_returns_path(mock_supabase):
    mock_supabase.storage.from_.return_value.upload.return_value = MagicMock(path="scans/hotel-1/scan-1.jpg")
    path = upload_scan_image(
        db=mock_supabase,
        hotel_id="hotel-1",
        scan_id="scan-1",
        image_bytes=b"fakejpeg",
    )
    assert path == "scans/hotel-1/scan-1.jpg"
    mock_supabase.storage.from_.assert_called_with("scan-images")


def test_delete_scan_image_calls_remove(mock_supabase):
    delete_scan_image(db=mock_supabase, path="scans/hotel-1/scan-1.jpg")
    mock_supabase.storage.from_.return_value.remove.assert_called_once_with(["scans/hotel-1/scan-1.jpg"])


def test_get_signed_url_returns_url(mock_supabase):
    mock_supabase.storage.from_.return_value.create_signed_url.return_value = {
        "signedURL": "https://signed.example.com/scan.jpg"
    }
    url = get_signed_url(db=mock_supabase, path="scans/hotel-1/scan-1.jpg", expires_in=300)
    assert url == "https://signed.example.com/scan.jpg"
