# agent/tests/test_pii_guard.py
import pytest
from src.models import ScanData
from src.pii_guard import wipe, wipe_dict, PII_FIELD_NAMES


def _full_scan() -> ScanData:
    return ScanData(
        scan_id="abc123",
        pms_profile_name="opera",
        last_name="Smith",
        first_name="John",
        dob="01/15/1990",
        doc_number="A12345678",
        address_line_1="123 Main St",
        address_line_2="Apt 4B",
        city="Springfield",
        postal_code="12345",
        email="john.smith@example.com",
    )


class TestWipe:
    def test_zeroes_all_pii_string_fields(self):
        scan = _full_scan()
        wipe(scan)
        for field in PII_FIELD_NAMES:
            val = getattr(scan, field, None)
            assert val == "" or val is None, f"field {field!r} not zeroed: {val!r}"

    def test_preserves_non_pii_fields(self):
        """scan_id and pms_profile_name are audit fields — kept after wipe."""
        scan = _full_scan()
        wipe(scan)
        assert scan.scan_id == "abc123"
        assert scan.pms_profile_name == "opera"

    def test_wipe_handles_none_field_values(self):
        """Fields already None must remain None (not raise)."""
        scan = ScanData(
            scan_id="abc123",
            pms_profile_name="opera",
            last_name=None,
            first_name="John",
        )
        wipe(scan)  # must not raise
        assert scan.first_name == ""
        assert scan.last_name is None

    def test_wipe_is_idempotent(self):
        scan = _full_scan()
        wipe(scan)
        wipe(scan)  # second call must not raise

    def test_wipe_none_is_noop(self):
        wipe(None)  # must not raise


class TestWipeDict:
    def test_zeroes_pii_keys_in_dict(self):
        d = {k: f"val_{k}" for k in PII_FIELD_NAMES}
        d["scan_id"] = "abc123"
        wipe_dict(d)
        for k in PII_FIELD_NAMES:
            assert d[k] == ""
        assert d["scan_id"] == "abc123"

    def test_ignores_missing_keys(self):
        d = {"last_name": "Smith"}
        wipe_dict(d)  # must not raise on missing keys
        assert d["last_name"] == ""
