# backend/tests/test_retention.py
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.storage = MagicMock()
    return db


def test_delete_expired_images_deletes_storage_and_nulls_path(mock_db):
    from app.services.retention import delete_expired_images

    mock_db.table.return_value.select.return_value.not_.return_value.lte.return_value.execute.return_value = MagicMock(
        data=[
            {"id": "scan-1", "hotel_id": "hotel-1", "image_path": "scans/hotel-1/scan-1.jpg"},
            {"id": "scan-2", "hotel_id": "hotel-1", "image_path": "scans/hotel-1/scan-2.jpg"},
        ]
    )
    mock_db.table.return_value.update.return_value.in_.return_value.execute.return_value = MagicMock(data=[])

    delete_expired_images(db=mock_db)

    mock_db.storage.from_.return_value.remove.assert_called()


def test_delete_expired_images_noop_when_none_expired(mock_db):
    from app.services.retention import delete_expired_images

    mock_db.table.return_value.select.return_value.not_.return_value.lte.return_value.execute.return_value = MagicMock(
        data=[]
    )

    delete_expired_images(mock_db)

    mock_db.storage.from_.return_value.remove.assert_not_called()
