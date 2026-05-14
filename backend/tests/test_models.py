import pytest
from pydantic import ValidationError
from app.models.common import ApiResponse, PaginatedResponse
from app.models.scan import ParsedID, ScanResponse
from app.models.guest import GuestResponse, GuestListItem


def test_api_response_ok():
    r = ApiResponse.ok({"id": "123"})
    assert r.success is True
    assert r.data == {"id": "123"}
    assert r.error is None


def test_api_response_fail():
    r = ApiResponse.fail("Something went wrong")
    assert r.success is False
    assert r.error == "Something went wrong"
    assert r.data is None


def test_parsed_id_all_none_by_default():
    p = ParsedID()
    assert p.first_name is None
    assert p.confidence == 0.0


def test_parsed_id_confidence_too_high_raises():
    with pytest.raises(ValidationError):
        ParsedID(confidence=1.5)


def test_parsed_id_confidence_too_low_raises():
    with pytest.raises(ValidationError):
        ParsedID(confidence=-0.1)


def test_scan_response_minimal():
    s = ScanResponse(
        id="scan-1", status="parsed",
        face_region_blacked_out=True, created_at="2026-05-14T00:00:00Z"
    )
    assert s.face_region_blacked_out is True
    assert s.parsed_data is None


def test_guest_list_item():
    g = GuestListItem(id="g-1", first_name="J", last_name="Doe",
                      doc_type="passport", doc_number_last4="6789",
                      created_at="2026-05-14T00:00:00Z")
    assert g.doc_number_last4 == "6789"
