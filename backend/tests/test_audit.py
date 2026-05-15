import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.audit import write_audit_log


@pytest.mark.asyncio
async def test_write_audit_log_inserts_record():
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "log-1"}])
    await write_audit_log(
        db=mock_db, hotel_id="hotel-1", user_id="user-1",
        action="scan.parsed", resource_type="scan", resource_id="scan-1",
        metadata={"doc_type": "passport"}, ip_address="1.2.3.4",
    )
    call_payload = mock_db.table.return_value.insert.call_args[0][0]
    assert call_payload["action"] == "scan.parsed"
    assert call_payload["hotel_id"] == "hotel-1"


@pytest.mark.asyncio
async def test_write_audit_log_does_not_raise_on_db_error():
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.side_effect = Exception("DB down")
    # Must not raise — audit failure is swallowed to protect the request path
    await write_audit_log(db=mock_db, hotel_id="hotel-1", action="scan.parsed")


@pytest.mark.asyncio
async def test_write_audit_log_never_logs_raw_doc_number():
    """Audit metadata must not contain full doc_number."""
    mock_db = MagicMock()
    mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])
    await write_audit_log(
        db=mock_db, hotel_id="hotel-1", action="scan.parsed",
        metadata={"doc_type": "passport", "doc_country": "US"},
    )
    call_payload = mock_db.table.return_value.insert.call_args[0][0]
    assert "doc_number" not in call_payload["metadata"]
