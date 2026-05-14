# backend/tests/test_pii_scrubber.py
from app.utils.pii import mask_name, mask_doc_number, scrub_pii_from_string
from app.utils.logging import _pii_scrub_processor


def test_mask_name_returns_initial_plus_last():
    assert mask_name("John", "Smith") == "J. Smith"


def test_mask_name_no_first():
    assert mask_name(None, "Smith") == "Smith"


def test_mask_name_only_first():
    assert mask_name("John", None) == "J."


def test_mask_name_empty_first_with_last():
    assert mask_name("", "Smith") == "Smith"


def test_mask_name_empty_first_no_last():
    assert mask_name("", None) == ""


def test_mask_name_both_none():
    assert mask_name(None, None) == ""


def test_mask_doc_number_shows_last_four():
    assert mask_doc_number("AB123456789") == "****6789"


def test_mask_doc_number_exactly_four_chars():
    assert mask_doc_number("A123") == "****A123"


def test_mask_doc_number_short():
    assert mask_doc_number("AB1") == "****"


def test_mask_doc_number_none():
    assert mask_doc_number(None) is None


def test_scrub_pii_redacts_dob():
    result = scrub_pii_from_string("guest dob=1990-05-12 checked in")
    assert "1990-05-12" not in result
    assert "[DOB_REDACTED]" in result


def test_scrub_pii_redacts_explicit_doc_number_and_shows_mask():
    result = scrub_pii_from_string("doc_number=AB123456")
    assert "AB123456" not in result
    assert "doc_number" in result  # key prefix preserved
    assert "****" in result        # masked value present


def test_scrub_pii_preserves_version_strings():
    result = scrub_pii_from_string("running version v1234 of the app")
    assert "v1234" in result


def test_pii_scrub_processor_removes_all_pii_keys():
    event_dict = {
        "event": "guest created",
        "first_name": "John",
        "last_name": "Smith",
        "dob": "1990-01-01",
        "doc_number": "AB123456",
        "email": "john@example.com",
        "phone": "555-1234",
        "address": "123 Main St",
        "hotel_id": "hotel-uuid",
    }
    result = _pii_scrub_processor(None, None, event_dict)
    for pii_key in ("first_name", "last_name", "dob", "doc_number", "email", "phone", "address"):
        assert pii_key not in result, f"{pii_key} should be removed"
    assert result["hotel_id"] == "hotel-uuid"


def test_pii_scrub_processor_scrubs_dob_in_event_string():
    """PII in the event string itself should be scrubbed."""
    event_dict = {"event": "scan created on 1990-05-12 for hotel", "hotel_id": "h-1"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert "1990-05-12" not in result["event"]
    assert "[DOB_REDACTED]" in result["event"]


def test_pii_scrub_processor_preserves_non_pii_event():
    event_dict = {"event": "scan.parsed scan_id=abc-123"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result["event"] == "scan.parsed scan_id=abc-123"


def test_pii_scrub_processor_handles_missing_keys_gracefully():
    event_dict = {"event": "system startup", "level": "info"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result["event"] == "system startup"


def test_pii_scrub_processor_handles_non_string_event():
    event_dict = {"event": 42, "level": "info"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result["event"] == 42


def test_pii_scrub_processor_mutates_in_place():
    """Verify processor returns same dict object (structlog contract)."""
    event_dict = {"event": "ok", "first_name": "Jane"}
    result = _pii_scrub_processor(None, None, event_dict)
    assert result is event_dict
